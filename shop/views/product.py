# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils.translation import get_language_from_request
from rest_framework import generics
from rest_framework import status
from rest_framework import views
from rest_framework.renderers import BrowsableAPIRenderer
from rest_framework.response import Response
from shop.rest.money import JSONRenderer
from shop.rest.serializers import AddToCartSerializer
from shop.rest.renderers import CMSPageRenderer
from shop.models.product import ProductModel


class ProductListView(generics.ListAPIView):
    renderer_classes = (CMSPageRenderer, JSONRenderer, BrowsableAPIRenderer)
    product_model = ProductModel
    serializer_class = None  # must be overridden by ProductListView.as_view
    filter_class = None  # may be overridden by ProductListView.as_view
    limit_choices_to = Q()

    def get_queryset(self):
        filter_kwargs = {}
        if hasattr(self.product_model, 'translations'):
            filter_kwargs.update(translations__language_code=get_language_from_request(self.request))
        qs = self.product_model.objects.filter(self.limit_choices_to, **filter_kwargs)

        # restrict products for current CMS page
        current_page = self.request.current_page
        if current_page.publisher_is_draft:
            current_page = current_page.publisher_public
        qs = qs.filter(cms_pages=current_page)
        return qs

    def get_template_names(self):
        return [self.request.current_page.get_template()]

    def paginate_queryset(self, queryset):
        page = super(ProductListView, self).paginate_queryset(queryset)
        self.paginator = page.paginator
        return page

    def filter_queryset(self, queryset):
        self.filter_context = None
        if self.filter_class:
            filter_instance = self.filter_class(self.request.query_params, queryset=queryset)
            if callable(getattr(filter_instance, 'get_render_context', None)):
                self.filter_context = filter_instance.get_render_context()
            elif hasattr(filter_instance, 'render_context'):
                self.filter_context = filter_instance.render_context
        qs = super(ProductListView, self).filter_queryset(queryset)
        print qs.query
        return qs

    def get_renderer_context(self):
        renderer_context = super(ProductListView, self).get_renderer_context()
        if renderer_context['request'].accepted_renderer.format == 'html':
            # add the paginator as Python object to the context
            renderer_context['paginator'] = self.paginator
            renderer_context['filter'] = self.filter_context
        return renderer_context


class AddToCartView(views.APIView):
    """
    Handle the "Add to Cart" dialog on the products detail page.
    """
    renderer_classes = (JSONRenderer, BrowsableAPIRenderer)
    product_model = ProductModel
    serializer_class = AddToCartSerializer
    lookup_field = lookup_url_kwarg = 'slug'
    limit_choices_to = Q()

    def get_context(self, request, **kwargs):
        assert self.lookup_url_kwarg in kwargs
        filter_kwargs = {self.lookup_field: kwargs.pop(self.lookup_url_kwarg)}
        if hasattr(self.product_model, 'translations'):
            filter_kwargs.update(translations__language_code=get_language_from_request(self.request))
        queryset = self.product_model.objects.filter(self.limit_choices_to, **filter_kwargs)
        product = get_object_or_404(queryset)
        return {'product': product, 'request': request}

    def get(self, request, *args, **kwargs):
        context = self.get_context(request, **kwargs)
        serializer = self.serializer_class(context=context)
        return Response(serializer.data)

    def post(self, request, *args, **kwargs):
        context = self.get_context(request, **kwargs)
        serializer = self.serializer_class(data=request.data, context=context)
        if serializer.is_valid():
            return Response(serializer.data, status=status.HTTP_202_ACCEPTED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProductRetrieveView(generics.RetrieveAPIView):
    """
    View responsible for rendering the products details.
    Additionally an extra method as shown in products lists, cart lists
    and order item lists.
    """
    renderer_classes = (CMSPageRenderer, JSONRenderer, BrowsableAPIRenderer)
    lookup_field = lookup_url_kwarg = 'slug'
    product_model = ProductModel
    serializer_class = None  # must be overridden by ProductListView.as_view
    limit_choices_to = Q()

    def get_template_names(self):
        product = self.get_object()
        app_label = product._meta.app_label.lower()
        basename = 'catalog-detail-{}.html'.format(product.__class__.__name__.lower())
        return [
            os.path.join(app_label, 'pages', basename),
            os.path.join(app_label, 'pages/catalog-detail-product.html'),
            'shop/pages/catalog-detail-product.html',
        ]

    def get_renderer_context(self):
        renderer_context = super(ProductRetrieveView, self).get_renderer_context()
        if renderer_context['request'].accepted_renderer.format == 'html':
            # add the product as Python object to the context
            renderer_context['product'] = self.get_object()
        return renderer_context

    def get_object(self):
        if not hasattr(self, '_product'):
            assert self.lookup_url_kwarg in self.kwargs
            filter_kwargs = {self.lookup_field: self.kwargs[self.lookup_url_kwarg]}
            if hasattr(self.product_model, 'translations'):
                filter_kwargs.update(translations__language_code=get_language_from_request(self.request))
            queryset = self.product_model.objects.filter(self.limit_choices_to, **filter_kwargs)
            product = get_object_or_404(queryset)
            self._product = product
        return self._product
