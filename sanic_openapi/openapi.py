import re
from itertools import repeat

from sanic.blueprints import Blueprint
from sanic.response import json
from sanic.views import CompositionView

from .doc import route_specs, RouteSpec, serialize_schema, definitions, excluded_static

import logging

blueprint = Blueprint('openapi', url_prefix='openapi')

_spec = {}


# Removes all null values from a dictionary
def remove_nulls(dictionary, deep=True):
    return {
        k: remove_nulls(v, deep) if deep and type(v) is dict else v
        for k, v in dictionary.items()
        if v is not None
    }


@blueprint.listener('before_server_start')
def build_spec(app, loop):
    _spec['swagger'] = '2.0'
    _spec['info'] = {
        "version": getattr(app.config, 'API_VERSION', '1.0.0'),
        "title": getattr(app.config, 'API_TITLE', 'API'),
        "description": getattr(app.config, 'API_DESCRIPTION', ''),
        "termsOfService": getattr(app.config, 'API_TERMS_OF_SERVICE', None),
        "contact": {
            "email": getattr(app.config, 'API_CONTACT_EMAIL', None)
        },
        "license": {
            "email": getattr(app.config, 'API_LICENSE_NAME', None),
            "url": getattr(app.config, 'API_LICENSE_URL', None)
        }
    }
    _spec['host'] = getattr(app.config, 'API_HOST', None)
    _spec['basePath'] = getattr(app.config, 'API_BASE_PATH', None)
    _spec['schemes'] = getattr(app.config, 'API_SCHEMES', ['http'])

    # --------------------------------------------------------------- #
    # Security Definitions
    # --------------------------------------------------------------- #

    _spec['securityDefinitions'] = {
        "x-api-key": {
            "type": 'apiKey',
            "name": 'x-api-key',
            "in": 'header'
        }
    }

    # --------------------------------------------------------------- #
    # Blueprint Tags
    # --------------------------------------------------------------- #

    for blueprint in app.blueprints.values():
        if hasattr(blueprint, 'routes'):
            for route in blueprint.routes:
                route_spec = route_specs[route.handler]
                route_spec.blueprint = blueprint
                if not route_spec.tags:
                    route_spec.tags.append(blueprint.name)

    paths = {}

    dedupe_routes = []
    seen = set()
    for x in app.router.routes_all.items():
        uri = x[0][:-1] if x[0].endswith('/') else x[0]
        if uri not in seen:
            dedupe_routes.append(x)
            seen.add(uri)

    for uri, route in dedupe_routes:
        if any(uri.startswith(path) for path in excluded_static) \
                or '<file_uri' in uri:
            continue

        # --------------------------------------------------------------- #
        # Methods
        # --------------------------------------------------------------- #

        # Build list of methods and their handler functions
        handler_type = type(route.handler)
        if handler_type is CompositionView:
            view = route.handler
            method_handlers = view.handlers.items()
        else:
            method_handlers = zip(route.methods, repeat(route.handler))

        methods = {}
        for _method, _handler in method_handlers:
            route_spec = route_specs.get(_handler) or RouteSpec()
            if _method == 'OPTIONS' or route_spec.exclude:
                continue
            consumes_content_types = route_spec.consumes_content_type or \
                getattr(app.config, 'API_CONSUMES_CONTENT_TYPES', ['application/json'])
            produces_content_types = route_spec.produces_content_type or \
                getattr(app.config, 'API_PRODUCES_CONTENT_TYPES', ['application/json'])

            # Path Parameters
            route_parameters = []
            for parameter in route.parameters:
                route_parameters.append({
                    **serialize_schema(parameter.cast),
                    'required': True,
                    'in': 'path',
                    'name': parameter.name
                })

            # Query String Parameters
            for name, parameter in route_spec.parameters.items():
                spec = serialize_schema(parameter.field)
                route_param = {
                    **spec,
                    'required': parameter.required,
                    'in': parameter.location,
                    'name': name
                }
                route_parameters.append(route_param)

            for consumer in route_spec.consumes:
                spec = serialize_schema(consumer.field)
                if 'properties' in spec:
                    for name, prop_spec in spec['properties'].items():
                        route_param = {
                            **prop_spec,
                            'required': consumer.required,
                            'in': consumer.location,
                            'name': name
                        }
                        route_parameters.append(route_param)
                else:
                    route_param = {
                        **spec,
                        'required': consumer.required,
                        'in': consumer.location,
                        'name': consumer.field.name if hasattr(consumer.field, 'name') else 'body'
                    }
                    if '$ref' in route_param:
                        route_param["schema"] = {'$ref': route_param['$ref']}
                        del route_param['$ref']
                    route_parameters.append(route_param)

            # Optional add Security by default
            # security = []
            # security.append({'x-api-key': []})
            # if len(route_spec.security) == 0:
            #     route_spec.security = security

            # Responses - Add Default Response
            if 200 not in route_spec.responses:
                route_spec.responses['200'] = {
                    "description": 'Successful Operation',
                    "example": None,
                    "schema": serialize_schema(route_spec.produces.field) if route_spec.produces else None
                }

            endpoint = remove_nulls({
                'operationId': route_spec.operation or route.name,
                'summary': route_spec.summary,
                'description': route_spec.description,
                'consumes': consumes_content_types,
                'produces': produces_content_types,
                'tags': route_spec.tags or None,
                'parameters': route_parameters,
                'responses': route_spec.responses,
                'security': route_spec.security,
                'deprecated': route_spec.deprecated
            })

            methods[_method.lower()] = endpoint

        uri_parsed = uri
        for parameter in route.parameters:
            uri_parsed = re.sub('<' + parameter.name + '.*?>', '{' + parameter.name + '}', uri_parsed)

        paths[uri_parsed] = methods

    # --------------------------------------------------------------- #
    # Definitions
    # --------------------------------------------------------------- #

    _spec['definitions'] = {obj.object_name: definition for cls, (obj, definition) in definitions.items()}

    _spec['paths'] = paths


@blueprint.route('/spec.json')
def spec(request):
    return json(_spec)
