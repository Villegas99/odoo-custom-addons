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
        readonly=True,
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

    saldo_original = fields.Monetary(
        string="Saldo Original",
        currency_field="currency_id",
        help="Monto inicial asignado manualmente a la caja chica."
    )

    saldo_actual = fields.Monetary(
        string="Saldo Actual",
        currency_field="currency_id",
        compute="_compute_saldo_actual",
        store=True,
        readonly=True,
        help="Saldo disponible calculado en tiempo real."
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

    @api.depends(
        'saldo_original',
        'x_studio_gasto',
        'x_studio_gasto.total_amount_currency'
    )
    def _compute_saldo_actual(self):
        for rec in self:
            if not rec.is_caja_chica_wallet:
                rec.saldo_actual = 0.0
                continue

            total_gastos_asociados = sum(
                rec.x_studio_gasto.mapped('total_amount_currency')
            )
            rec.saldo_actual = (rec.saldo_original or 0.0) - total_gastos_asociados

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
                and not rec.saldo_original
                and rec.total_amount_currency > 0
            ):
                rec.saldo_original = rec.total_amount_currency

    def _get_currency_rounding(self):
        self.ensure_one()
        currency = self.currency_id or self.company_id.currency_id
        return currency.rounding if currency else 0.01

    def _get_expense_amount(self):
        self.ensure_one()
        return self.total_amount_currency or 0.0

    def _build_result_notification(self, gastos_procesados, errores, titulo='Resultado'):
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

    def _validate_posted_state(self):
        for rec in self:
            if rec.state != 'posted':
                raise UserError(_(
                    "Esta acción solo se puede ejecutar cuando el gasto está en estado Posted."
                ))

    def action_balance_caja_chica(self):
        gastos_procesados = 0
        errores = []

        for gasto in self:
            try:
                gasto._validate_posted_state()
                rounding = gasto._get_currency_rounding()

                if gasto.is_caja_chica_wallet:
                    raise UserError(_("No se puede ejecutar 'Asociar Gasto' sobre una bolsa de Caja Chica."))

                monto_origen = gasto._get_expense_amount()
                if float_compare(monto_origen, 0.0, precision_rounding=rounding) <= 0:
                    raise UserError(_("El gasto debe tener un monto positivo para asociarse."))

                if not gasto.x_studio_caja_chica:
                    raise UserError(_("No hay una caja chica asociada al gasto."))

                caja_chica = gasto.x_studio_caja_chica

                if not caja_chica.exists():
                    raise UserError(_("La caja chica asociada ya no existe."))

                if not caja_chica.is_caja_chica_wallet:
                    raise UserError(_("El registro asociado no pertenece a la categoría Caja Chica."))

                if caja_chica.id == gasto.id:
                    raise UserError(_("Un gasto no puede asociarse a sí mismo como caja chica."))

                if gasto.id in caja_chica.x_studio_gasto.ids:
                    raise UserError(_("Este gasto ya está asociado a la caja chica seleccionada."))

                if float_compare(caja_chica.saldo_actual, monto_origen, precision_rounding=rounding) < 0:
                    raise UserError(_(
                        "Saldo insuficiente en caja chica.\n"
                        "• Monto a asociar: %(monto)s\n"
                        "• Saldo actual disponible: %(saldo)s",
                        monto=monto_origen,
                        saldo=caja_chica.saldo_actual,
                    ))

                caja_chica.write({
                    'x_studio_gasto': [(4, gasto.id)]
                })

                # Releer para mostrar saldo recalculado
                caja_chica.flush_recordset()
                caja_chica.invalidate_recordset(['saldo_actual'])

                gasto.message_post(body=_(
                    "✅ Gasto asociado a caja chica<br/>"
                    "• Caja chica: %(caja)s<br/>"
                    "• Monto del gasto: %(monto)s<br/>"
                    "• Saldo actual disponible después de la asociación: %(saldo)s",
                    caja=caja_chica.display_name,
                    monto=monto_origen,
                    saldo=caja_chica.saldo_actual,
                ))

                caja_chica.message_post(body=_(
                    "🔁 Gasto asociado a la caja chica<br/>"
                    "• Gasto origen: %(gasto)s<br/>"
                    "• Monto asociado: %(monto)s<br/>"
                    "• Saldo actual disponible: %(saldo)s",
                    gasto=gasto.display_name,
                    monto=monto_origen,
                    saldo=caja_chica.saldo_actual,
                ))

                gastos_procesados += 1

            except Exception as e:
                error_msg = str(e)
                try:
                    gasto.message_post(body=_("❌ Error en la asociación: %s", error_msg))
                except Exception:
                    pass
                errores.append(f"{gasto.display_name}: {error_msg}")

        return self._build_result_notification(
            gastos_procesados=gastos_procesados,
            errores=errores,
            titulo=_('Resultado de asociación')
        )

    def action_reajuste_caja_chica(self):
        gastos_procesados = 0
        errores = []

        for gasto in self:
            try:
                gasto._validate_posted_state()
                rounding = gasto._get_currency_rounding()

                if gasto.is_caja_chica_wallet:
                    raise UserError(_("No se puede ejecutar 'Desasociar Gasto' sobre una bolsa de Caja Chica."))

                monto_origen = gasto._get_expense_amount()
                if float_compare(monto_origen, 0.0, precision_rounding=rounding) <= 0:
                    raise UserError(_("El gasto debe tener un monto positivo para desasociarse."))

                if not gasto.x_studio_caja_chica:
                    raise UserError(_("No hay una caja chica asociada al gasto."))

                caja_chica = gasto.x_studio_caja_chica

                if not caja_chica.exists():
                    raise UserError(_("La caja chica asociada ya no existe."))

                if not caja_chica.is_caja_chica_wallet:
                    raise UserError(_("El registro asociado no pertenece a la categoría Caja Chica."))

                if gasto.id not in caja_chica.x_studio_gasto.ids:
                    raise UserError(_("Este gasto no está vinculado activamente a la caja chica."))

                caja_chica.write({
                    'x_studio_gasto': [(3, gasto.id)]
                })

                # Releer para mostrar saldo recalculado
                caja_chica.flush_recordset()
                caja_chica.invalidate_recordset(['saldo_actual'])

                gasto.message_post(body=_(
                    "🔔 Gasto desasociado de caja chica<br/>"
                    "• Caja chica: %(caja)s<br/>"
                    "• Monto del gasto: %(monto)s<br/>"
                    "• Saldo actual disponible después de la desasociación: %(saldo)s",
                    caja=caja_chica.display_name,
                    monto=monto_origen,
                    saldo=caja_chica.saldo_actual,
                ))

                caja_chica.message_post(body=_(
                    "🔔 Gasto desasociado de la caja chica<br/>"
                    "• Gasto origen: %(gasto)s<br/>"
                    "• Monto desasociado: %(monto)s<br/>"
                    "• Saldo actual disponible: %(saldo)s",
                    gasto=gasto.display_name,
                    monto=monto_origen,
                    saldo=caja_chica.saldo_actual,
                ))

                gastos_procesados += 1

            except Exception as e:
                error_msg = str(e)
                try:
                    gasto.message_post(body=_("❌ Error en la desasociación: %s", error_msg))
                except Exception:
                    pass
                errores.append(f"{gasto.display_name}: {error_msg}")

        return self._build_result_notification(
            gastos_procesados=gastos_procesados,
            errores=errores,
            titulo=_('Resultado de desasociación')
        )