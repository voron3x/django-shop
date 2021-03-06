# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.db import models
from django.utils.translation import ugettext_lazy as _
from shop.models import order


class Order(order.BaseOrder):
    """Default materialized model for Order"""
    shipping_address_text = models.TextField(_("Shipping address"), blank=True, null=True,
        help_text=_("Shipping address at the moment of purchase."))
    billing_address_text = models.TextField(_("Billing address"), blank=True, null=True,
        help_text=_("Billing address at the moment of purchase."))

    def populate_from_cart(self, cart, request):
        super(Order, self).populate_from_cart(cart, request)
        self.shipping_address_text = cart.shipping_address.as_text()
        self.billing_address_text = cart.shipping_address.as_text()
