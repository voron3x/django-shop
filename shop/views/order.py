# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from rest_framework import generics, mixins
from rest_framework.renderers import BrowsableAPIRenderer
from shop.rest.serializers import OrderListSerializer, OrderDetailSerializer
from shop.rest.money import JSONRenderer
from shop.rest.renderers import CMSPageRenderer
from shop.models.order import OrderModel


class OrderView(mixins.ListModelMixin, mixins.RetrieveModelMixin, generics.GenericAPIView):
    """
    Base View class to render the fulfilled orders for the current user.
    """
    renderer_classes = (CMSPageRenderer, JSONRenderer, BrowsableAPIRenderer)
    many = True

    def get_queryset(self):
        return OrderModel.objects.filter(user=self.request.user).order_by('-updated_at',)

    def get_serializer_class(self):
        if self.many:
            return OrderListSerializer
        return OrderDetailSerializer

    def get_renderer_context(self):
        renderer_context = super(OrderView, self).get_renderer_context()
        if renderer_context['request'].accepted_renderer.format == 'html':
            # in edit_mode, both tables, for list- and detail view are rendered
            edit_mode = renderer_context['request'].current_page.publisher_is_draft
            renderer_context.update(many=self.many, edit_mode=edit_mode)
        return renderer_context

    def get_template_names(self):
        return [self.request.current_page.get_template()]

    def get_object(self):
        if self.lookup_field not in self.kwargs:
            return self.get_queryset().first()
        return super(OrderView, self).get_object()

    def get(self, request, *args, **kwargs):
        if self.is_last():
            self.many = False
        if self.many:
            return self.list(request, *args, **kwargs)
        return self.retrieve(request, *args, **kwargs)

    def is_last(self):
        """
        Return true, if the last order shall be rendered.
        Useful to render a Thank-You view immediately after a purchase.
        """
        return self.request.current_page.reverse_id == 'shop-order-last'
