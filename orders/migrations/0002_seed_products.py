"""
Mr Store — Initial UC Product Seed Migration

Creates a sensible starter catalog of PUBG UC packages
for the Nigerian market. Adjust prices/SKUs to match your wholesaler.
"""
from django.db import migrations


INITIAL_PRODUCTS = [
    {
        'name':      '60 UC',
        'sku':       'PUBG_NG_60UC',
        'uc_amount': 60,
        'price_ngn': 750.00,
        'badge':     '',
        'is_active': True,
    },
    {
        'name':      '325 UC',
        'sku':       'PUBG_NG_325UC',
        'uc_amount': 325,
        'price_ngn': 3500.00,
        'badge':     '',
        'is_active': True,
    },
    {
        'name':      '660 UC',
        'sku':       'PUBG_NG_660UC',
        'uc_amount': 660,
        'price_ngn': 6500.00,
        'badge':     '🔥 Best Value',
        'is_active': True,
    },
    {
        'name':      '1800 UC',
        'sku':       'PUBG_NG_1800UC',
        'uc_amount': 1800,
        'price_ngn': 17000.00,
        'badge':     '',
        'is_active': True,
    },
    {
        'name':      '3850 UC',
        'sku':       'PUBG_NG_3850UC',
        'uc_amount': 3850,
        'price_ngn': 34000.00,
        'badge':     '💎 Most Popular',
        'is_active': True,
    },
    {
        'name':      '8100 UC',
        'sku':       'PUBG_NG_8100UC',
        'uc_amount': 8100,
        'price_ngn': 68000.00,
        'badge':     '',
        'is_active': True,
    },
]


def seed_products(apps, schema_editor):
    Product = apps.get_model('orders', 'Product')
    for data in INITIAL_PRODUCTS:
        Product.objects.get_or_create(sku=data['sku'], defaults=data)


def unseed_products(apps, schema_editor):
    Product = apps.get_model('orders', 'Product')
    skus = [p['sku'] for p in INITIAL_PRODUCTS]
    Product.objects.filter(sku__in=skus).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('orders', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed_products, reverse_code=unseed_products),
    ]
