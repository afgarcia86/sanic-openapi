# Sanic OpenAPI

[![Build Status](https://travis-ci.org/channelcat/sanic-openapi.svg?branch=master)](https://travis-ci.org/channelcat/sanic-openapi)
[![PyPI](https://img.shields.io/pypi/v/sanic-openapi.svg)](https://pypi.python.org/pypi/sanic-openapi/)
[![PyPI](https://img.shields.io/pypi/pyversions/sanic-openapi.svg)](https://pypi.python.org/pypi/sanic-openapi/)

Give your Sanic API a UI and OpenAPI documentation, all for the price of free!

![Example Swagger UI](images/code-to-ui.png?raw=true "Swagger UI")

## Installation

```shell
pip install sanic-openapi
```

Add OpenAPI and Swagger UI:

```python
from sanic_openapi import swagger_blueprint, openapi_blueprint

app.blueprint(openapi_blueprint)
app.blueprint(swagger_blueprint)
```

You'll now have a Swagger UI at the URL `/swagger`.  
Your routes will be automatically categorized by their blueprints.

## Example

For an example Swagger UI, see the [Pet Store](http://petstore.swagger.io/)

## Usage

### Use simple decorators to document routes:

```python
from sanic_openapi import doc

@app.get("/user/<user_id:int>")
@doc.summary("Fetches a user by ID")
@doc.produces({ "user": { "name": str, "id": int } })
@doc.response(200, 'Successful')
@doc.response(404, 'Not found')
async def get_user(request, user_id):
    ...

@app.post("/user")
@doc.summary("Creates a user")
@doc.consumes({"user": { "name": str }}, location="body")
@doc.response(201, 'Created')
async def create_user(request):
    ...
```

### Model your input/output

```python
class Car:
    make = str
    model = str
    year = int

class Garage:
    spaces = int
    cars = [Car]

@app.get("/garage")
@doc.summary("Gets the whole garage")
@doc.produces(Garage)
async def get_garage(request):
    return json({
        "spaces": 2,
        "cars": [{"make": "Nissan", "model": "370Z"}]
    })

```

### Detailed Responses

```
@doc.response(code=300, description="testing", examples={"user": {"name": str}}, schema=doc.List(NewDataset))
```

### Get more descriptive

```python
class InnerNestedObject():
    name = doc.String("this is crazy", example="look", default="I am the default")
    array = doc.List([doc.String(example="im inside")], "no its not")


class NestedObject():
    name = doc.String("some name", example="hello world", required=True)
    array = doc.List([doc.String(example="sample string")], "An array in the nested object", required=True)
    inner_nested = doc.Object(InnerNestedObject, "A dream inside a dream", required=True)


class ParentDataset():
    name = doc.String("The name of the parent object.", required=True, example="DemoObject")
    example_list = doc.List([
        doc.String(example="sample string")
    ], "example list description", required=True)
    nested = doc.Object(NestedObject, "example Nested Object", required=True)
```

### Add Security and Security Definitions

```python
from sanic_openapi import doc

@app.get("/auth_required")
@doc.security('x-api-key')
async def auth_required(request):
    ...
```
*securityDefinitions* 

in: openapi.py
```
_spec['securityDefinitions'] = {
        "x-api-key": {
            "type": 'apiKey',
            "name": 'x-api-key',
            "in": 'header'
        }
    }
```

### Exclude Routes
```python
from sanic_openapi import doc

@app.get("/private")
@doc.exclude(True)
async def private(request):
    ...
```

*Excluding Static*
```
doc.excluded_static.add('/favicon.ico')
app.static('/favicon.ico', favicon_path)
```

### Custom Menu Tags
```python
from sanic_openapi import doc

@app.get("/special")
@doc.tag('Special Menu')
async def special(request):
    ...
```

### Configure all the things

```python
app.config.API_VERSION = '1.0.0'
app.config.API_TITLE = 'Car API'
app.config.API_DESCRIPTION = 'Car API'
app.config.API_TERMS_OF_SERVICE = 'Use with caution!'
app.config.API_PRODUCES_CONTENT_TYPES = ['application/json']
app.config.API_CONTACT_EMAIL = 'channelcat@gmail.com'
```