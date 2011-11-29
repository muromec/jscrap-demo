import os
from werkzeug.wrappers import Request, Response
from simplejson import dumps
from biribiri import chain
from biribiri.chain.utils import upd_ctx, view, match
from jinja2 import Environment, FileSystemLoader

def f(filename, f=__file__, sep=""):
    path,_file = os.path.split(f)
    return os.path.join(path, sep, filename)

env = Environment( loader=FileSystemLoader( 
    [ f("templates") ]
))

@upd_ctx('tpl', 'nav')
def splash(**ctx):
    return 'splash.html', {
        "links": [
            {"url": "/plain", "name": "Plain",},
            {"url": "/js", "name": "Generated",},
            {"url": "/", "name": "Index"},
        ]
    }

@upd_ctx('dump_fields')
def json(**ctx):
    return [
            'url',
    ],None

@upd_ctx('body', 'ct')
def tpl(**ctx):
    from jinja2.parser import Parser
    from jscrap.generator import JsGenerator

    tpl = 'splash.html'

    source,_,_ = env.loader.get_source(env, tpl)
    code = Parser(env, source)
    gen = JsGenerator(env, tpl, tpl)
    gen.visit(code.parse())

    return gen.stream.getvalue(), 'text/plain'


def render(**ctx):
    return [render_html, render_json]

@match(tpl=basestring)
@upd_ctx('body')
def render_html(tpl, **ctx):
    tpl_o = env.get_template(tpl)

    return tpl_o.render(**ctx)

@match(dump_fields=list)
@upd_ctx('body', 'ct')
def render_json(dump_fields, **ctx):
    return dumps(dict([
        (field, ctx[field])
        for field in dump_fields
        if field in ctx
    ])),'text/json'


@upd_ctx('response')
def response(body=None, ct='text/html', **ctx):
    code = 202 if body else 404
    return Response(body or "Nani-Nani", status=code, content_type=ct)

@upd_ctx('url')
def route(request, **ctx):
    return request.path, handlers

@match(found_view=None, body=None)
@upd_ctx('body')
def static(url, **ctx):
    if not url.startswith('/static'):
        return

    _,static,package,path = url.split('/',3)
    if package not in ['jscrap', 'blog']:
        return

    mod = __import__(package)
    return open(f(path, mod.__file__, 'data'), 'rb')

handlers = [
        static,
        view('/json')(json),
        view('/tpl')(tpl),
        view('/')(splash),
        view('/plain')(splash),
]



@Request.application
def application(request):
    ret = chain.run([route, render, response], request=request)
    return ret['response']

if __name__ == '__main__':
    from werkzeug.serving import run_simple
    run_simple('0.0.0.0', 4000, application)
