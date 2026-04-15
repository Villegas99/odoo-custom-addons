# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools import float_compare


class HrExpenseCajaChica(models.Model):
    _inherit = 'hr.expense'

    is_caja_chica_wallet = fields.Boolean(
        string="Es Caja Chica (Bolsa)",
        compute="_compute_is_caja_chica_wallet",
        store=True,
        help="Indica si este gasto pertenece a la categoría Caja Chica y funciona como bolsa."
    )

    x_studio_gasto = fields.Many2many(
        comodel_name='hr.expense',
        relation='hr_expense_caja_chica_rel',
        column1='caja_chica_id',
        column2='gasto_id',
        string="Gastos Asociados",
        domain="[('is_caja_chica_wallet', '=', False)]",
        help="Gastos normales asociados a esta caja chica."
    )

    x_studio_gasto_de_caja_chica = fields.Boolean(
        string="Gasto de Caja Chica",
        help="Indica que este gasto se pagará con una caja chica."
    )

    x_studio_caja_chica = fields.Many2one(
        comodel_name='hr.expense',
        string="Caja Chica Asociada",
        domain="[('is_caja_chica_wallet', '=', True)]",
        help="Bolsa de caja chica desde la cual se descontará este gasto."
    )

    x_studio_saldo_caja_chica = fields.Monetary(
        string="Saldo Caja Chica",
        currency_field="currency_id",
        help="Saldo disponible de la bolsa de caja chica."
    )

    @api.depends('product_id', 'product_id.categ_id')
    def _compute_is_caja_chica_wallet(self):
        caja_chica_categ = self.env.ref(
            'gastos_caja_chica.product_category_caja_chica',
            raise_if_not_found=False
        )

        for rec in self:
            rec.is_caja_chica_wallet = bool(
                caja_chica_categ
                and rec.product_id
                and rec.product_id.categ_id
                and rec.product_id.categ_id.id == caja_chica_categ.id
            )

    @api.onchange('product_id', 'total_amount_currency')
    def _onchange_init_wallet_balance(self):
        caja_chica_categ = self.env.ref(
            'gastos_caja_chica.product_category_caja_chica',
            raise_if_not_found=False
        )
        for rec in self:
            if (
                caja_chica_categ
                and rec.product_id
                and rec.product_id.categ_id.id == caja_chica_categ.id
                and not rec.x_studio_saldo_caja_chica
                and rec.total_amount_currency > 0
            ):
                rec.x_studio_saldo_caja_chica = rec.total_amount_currency

    def _get_currency_rounding(self):
        self.ensure_one()
        currency = self.currency_id or self.company_id.currency_id
        return currency.rounding if currency else 0.01

    def _get_expense_amount(self):
        self.ensure_one()
        return self.total_amount_currency or 0.0

    def _get_wallet_balance(self):
        self.ensure_one()
        return self.x_studio_saldo_caja_chica or 0.0

    def _write_wallet_balance(self, new_balance):
        self.ensure_one()
        self.write({
            'x_studio_saldo_caja_chica': new_balance
        })

    def _build_result_notification(self, gastos_procesados, errores, titulo='Resultado de transferencia'):
        mensaje = f"Proceso completado: {gastos_procesados} gasto(s) procesado(s)"
        if errores:
            mensaje += f", {len(errores)} con error"

        if errores:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': titulo,
                    'message': mensaje,
                    'type': 'warning',
                    'sticky': False,
                    'next': {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'title': _('Detalle de errores'),
                            'message': '\n'.join(errores),
                            'type': 'warning',
                            'sticky': False,
                            'next': {
                                'type': 'ir.actions.client',
                                'tag': 'reload'
                            }
                        }
                    }
                }
            }

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': titulo,
                'message': mensaje,
                'type': 'success',
                'sticky': False,
                'next': {
                    'type': 'ir.actions.client',
                    'tag': 'reload'
                }
            }
        }

    def action_balance_caja_chica(self):
        gastos_procesados = 0
        errores = []

        for gasto in self:
            try:
                rounding = gasto._get_currency_rounding()

                if gasto.is_caja_chica_wallet:
                    raise UserError(_("No se puede ejecutar 'Balance de Caja Chica' sobre una bolsa de Caja Chica."))

                monto_origen = gasto._get_expense_amount()
                if float_compare(monto_origen, 0.0, precision_rounding=rounding) <= 0:
                    raise UserError(_("El gasto debe tener un monto positivo para transferir."))

                if not gasto.x_studio_caja_chica:
                    raise UserError(_("No hay una caja chica asociada al gasto."))

                caja_chica = gasto.x_studio_caja_chica

                if not caja_chica.exists():
                    raise UserError(_("La caja chica asociada ya no existe."))

                if not caja_chica.is_caja_chica_wallet:
                    raise UserError(_("El registro asociado no pertenece a la categoría Caja Chica."))

                if caja_chica.id == gasto.id:
                    raise UserError(_("Un gasto no puede asociarse a sí mismo como caja chica."))

                saldo_actual = caja_chica._get_wallet_balance()
                nuevo_saldo = saldo_actual - monto_origen

                if float_compare(nuevo_saldo, 0.0, precision_rounding=rounding) < 0:
                    raise UserError(_(
                        "Saldo insuficiente en caja chica.\n"
                        "• Monto a transferir: %(monto)s\n"
                        "• Saldo actual en caja chica: %(saldo)s",
                        monto=monto_origen,
                        saldo=saldo_actual,
                    ))

                if gasto.id in caja_chica.x_studio_gasto.ids:
                    raise UserError(_("Este gasto ya está asociado a la caja chica seleccionada."))

                caja_chica._write_wallet_balance(nuevo_saldo)

                caja_chica.write({
                    'x_studio_gasto': [(4, gasto.id)]
                })

                gasto.message_post(body=_(
                    "✅ Transferencia a caja chica realizada<br/>"
                    "• Gasto de caja chica: %(caja)s<br/>"
                    "• Monto transferido: %(monto)s<br/>"
                    "• Saldo anterior en caja chica: %(saldo_anterior)s<br/>"
                    "• Nuevo saldo en caja chica: %(saldo_nuevo)s",
                    caja=caja_chica.display_name,
                    monto=monto_origen,
                    saldo_anterior=saldo_actual,
                    saldo_nuevo=nuevo_saldo,
                ))

                caja_chica.message_post(body=_(
                    "🔁 Ajuste de saldo por transferencia<br/>"
                    "• Gasto origen: %(gasto)s<br/>"
                    "• Monto debitado: %(monto)s<br/>"
                    "• Saldo anterior: %(saldo_anterior)s<br/>"
                    "• Nuevo saldo: %(saldo_nuevo)s",
                    gasto=gasto.display_name,
                    monto=monto_origen,
                    saldo_anterior=saldo_actual,
                    saldo_nuevo=nuevo_saldo,
                ))

                gastos_procesados += 1

            except Exception as e:
                error_msg = str(e)
                try:
                    gasto.message_post(body=_("❌ Error en la transferencia: %s", error_msg))
                except Exception:
                    pass
                errores.append(f"{gasto.display_name}: {error_msg}")

        return self._build_result_notification(
            gastos_procesados=gastos_procesados,
            errores=errores,
            titulo=_('Resultado de transferencia')
        )

    def action_reajuste_caja_chica(self):
        gastos_procesados = 0
        errores = []

        for gasto in self:
            try:
                rounding = gasto._get_currency_rounding()

                if gasto.is_caja_chica_wallet:
                    raise UserError(_("No se puede ejecutar 'Reajuste de Caja Chica' sobre una bolsa de Caja Chica."))

                monto_origen = gasto._get_expense_amount()
                if float_compare(monto_origen, 0.0, precision_rounding=rounding) <= 0:
                    raise UserError(_("El gasto debe tener un monto positivo para reajustar."))

                if not gasto.x_studio_caja_chica:
                    raise UserError(_("No hay una caja chica asociada al gasto."))

                caja_chica = gasto.x_studio_caja_chica

                if not caja_chica.exists():
                    raise UserError(_("La caja chica asociada ya no existe."))

                if not caja_chica.is_caja_chica_wallet:
                    raise UserError(_("El registro asociado no pertenece a la categoría Caja Chica."))

                if gasto.id not in caja_chica.x_studio_gasto.ids:
                    raise UserError(_("Este gasto no está vinculado activamente a la caja chica."))

                saldo_actual = caja_chica._get_wallet_balance()
                nuevo_saldo = saldo_actual + monto_origen

                caja_chica._write_wallet_balance(nuevo_saldo)

                caja_chica.write({
                    'x_studio_gasto': [(3, gasto.id)]
                })

                gasto.message_post(body=_(
                    "🔔 Ajuste a caja chica realizado por corrección de registro<br/>"
                    "• Gasto de caja chica: %(caja)s<br/>"
                    "• Monto de ajuste: %(monto)s<br/>"
                    "• Saldo anterior en caja chica: %(saldo_anterior)s<br/>"
                    "• Saldo ajustado en caja chica: %(saldo_nuevo)s",
                    caja=caja_chica.display_name,
                    monto=monto_origen,
                    saldo_anterior=saldo_actual,
                    saldo_nuevo=nuevo_saldo,
                ))

                caja_chica.message_post(body=_(
                    "🔔 Reajuste de saldo por corrección de registro<br/>"
                    "• Gasto origen: %(gasto)s<br/>"
                    "• Monto reintegrado: %(monto)s<br/>"
                    "• Saldo anterior: %(saldo_anterior)s<br/>"
                    "• Nuevo saldo: %(saldo_nuevo)s",
                    gasto=gasto.display_name,
                    monto=monto_origen,
                    saldo_anterior=saldo_actual,
                    saldo_nuevo=nuevo_saldo,
                ))

                gastos_procesados += 1

            except Exception as e:
                error_msg = str(e)
                try:
                    gasto.message_post(body=_("❌ Error en el reajuste: %s", error_msg))
                except Exception:
                    pass
                errores.append(f"{gasto.display_name}: {error_msg}")

        return self._build_result_notification(
            gastos_procesados=gastos_procesados,
            errores=errores,
            titulo=_('Resultado de reajuste')
        )