# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in root directory
##############################################################################
from odoo import fields, api, exceptions, models


class ProductBarcode(models.Model):
    _name = 'product.barcode'
    _description = "List of BARCODE for a product."
    _order = 'sequence'

    name = fields.Char(string='BARCODE', size=13, required=True)
    sequence = fields.Integer(string='Sequence')
    product_id = fields.Many2one(
        string='Product',
        comodel_name='product.product',
        required=True)

    @api.onchange('name')
    def onchange_name(self):
        if isinstance(self.name, basestring) and not self.env['barcode.nomenclature'].check_ean(self.name):
            raise exceptions.Warning((
                'You provided an invalid "EAN13 Barcode" reference. You may '
                'use the "Internal Reference" field instead.'))

    @api.one
    @api.constrains('name')
    def _check_name(self):
        if isinstance(self.name, basestring) and not self.env['barcode.nomenclature'].check_ean(self.name):
            raise exceptions.Warning((
                'You provided an invalid "EAN13 Barcode" reference. You may '
                'use the "Internal Reference" field instead.'))
        eans = self.search([('id', '!=', self.id), ('name', '=', self.name)])
        if eans:
            raise exceptions.Warning((
                'The EAN13 Barcode "%s" already exists for product "%s"!') % (
                    self.name, eans[0].product_id.name))

    def _auto_init(self):
        exist = self._table_exist()
        res = super(ProductBarcode, self)._auto_init()
        if not exist:
            self._cr.execute('INSERT INTO %s (product_id, name, sequence) '
                       'SELECT id, barcode, 0 '
                       'FROM product_product '
                       'WHERE barcode != \'\'' % self._table)
        return res


class ProductProduct(models.Model):
    _inherit = 'product.product'

    barcode_ids = fields.One2many(
        comodel_name='product.barcode',
        inverse_name='product_id',
        string='Multiple Barcodes')
    barcode = fields.Char(
        string='Main Barcode',
        compute='_compute_ean13',
        store=True)

    @api.one
    @api.depends('barcode_ids')
    def _compute_ean13(self):
        if self.barcode_ids:
            if self.barcode != self.barcode_ids[0]:
                self.barcode = self.barcode_ids[0].name
        else:
            self.barcode = ''

    @api.one
    def _create_ean13(self, ean13):
        return self.env['product.barcode'].create({
            'product_id': self.id,
            'barcode': ean13})

    @api.model
    def create(self, vals):
        res = super(ProductProduct, self).create(vals)
        if 'barcode' in vals:
            self._create_ean13(res.ean13)
        return res

    @api.one
    def write(self, vals):
        if 'barcode' in vals:
            eans = [e for e in self.barcode_ids if e.name == self.barcode]
            if eans:
                eans.write({'name': vals['barcode']})
            else:
                self._create_ean13(vals['barcode'])
        return super(ProductProduct, self).write(vals)

    @api.model
    def search(self, domain, *args, **kwargs):
        if filter(lambda x: x[0] == 'barcode', domain):
            ean_operator = filter(lambda x: x[0] == 'barcode', domain)[0][1]
            ean_value = filter(lambda x: x[0] == 'barcode', domain)[0][2]
            eans = self.env['product.barcode'].search(
                [('name', ean_operator, ean_value)])
            domain = filter(lambda x: x[0] != 'barcode', domain)
            domain += [('barcode_ids', 'in', eans.ids)]
        return super(ProductProduct, self).search(domain, *args, **kwargs)
