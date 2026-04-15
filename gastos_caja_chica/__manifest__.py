{
    'name': 'Gastos Caja Chica',
    'version': '19.0.1.0.0',
    'category': 'Human Resources/Expenses',
    'summary': 'Gestión de Caja Chica para gastos en Odoo Community',
    'description': """
        Módulo para gestionar gastos de Caja Chica:
        - Gastos tipo "bolsa" con saldo disponible
        - Vinculación de gastos normales a cajas chicas
        - Botones Balance/Reajuste con validaciones
        - Notificaciones y registro en chatter
    """,
    'author': 'Tu Nombre',
    'website': 'https://tudominio.com',
    'license': 'LGPL-3',
    
    # Dependencias
    'depends': [
        'hr_expense',      # Módulo base de gastos
        'product',         # Para categorías de producto
    ],
    
    # Archivos a cargar
    'data': [
        # 'security/ir.model.access.csv',  # Si creas nuevos modelos
        'data/caja_chica_category.xml',  # Datos iniciales
        'views/hr_expense_views.xml',    # Vistas personalizadas
    ],
    
    # Demostraciones (opcional)
    # 'demo': ['demo/demo_data.xml'],
    
    # Configuración
    'installable': True,
    'application': False,
    'auto_install': False,
}