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

def accept(*know_mime):
    know_set = set(know_mime)
    def decorator(f):
        def wrapped(*a, **kw):

            request = kw.get('request')
            args = dict(request.args)
            for typ in know_mime:
                if typ in args:
                    return f

            mime = kw.get('mime') or set()
            if mime & know_set:
                return f

        return wrapped
    return decorator


@upd_ctx('tpl', 'dump_fields')
def splash(**ctx):
    return 'splash.html', [ 'nav', 'gen', 'post_list', 'url',],None

@upd_ctx('nav')
def load_links(**ctx):
    return {
        "links": [
            {"url": "/?js", "name": "Template source",},
            {"url": "/?json", "name": "As json",},
            {"url": "/plain", "name": "No js",},
            {"url": "/", "name": "Index"},
            {
                "url": "http://github.com/muromec/jscrap-demo",
                "name": "This demo source on github",
            },
            {
                "url": "http://github.com/muromec/jscrap",
                "name": "JInja-to-js compiler source on github",
            },

        ]
    }

@upd_ctx('post_list')
def blog_posts(**ctx):
    return [
            {
                "title": "JSCrap", 
                "body": "Something about jinja compiler",
                "link": "/blog/jscrap",
            },
            {
                "title": "kernel",
                "body": "Everything in kernel is kobject",
                "link": "/blog/kernel",
            }
    ],None

@upd_ctx('gen')
def gen_by(**ctx):
    import jinja2
    return "Jinja %s" % jinja2.__version__

@accept('text/javascript', 'js')
@upd_ctx('body', 'ct')
def dump_tpl(tpl, **ctx):
    from jinja2.parser import Parser
    from jscrap.generator import JsGenerator

    source,_,_ = env.loader.get_source(env, tpl)
    code = Parser(env, source)
    gen = JsGenerator(env, tpl, tpl)
    gen.visit(code.parse())

    return gen.stream.getvalue(), 'text/plain'


@accept('text/html')
@match(tpl=basestring)
@upd_ctx('body')
def render_html(tpl, **ctx):
    tpl_o = env.get_template(tpl)

    return tpl_o.render(**ctx)

@accept('json')
@match(dump_fields=list)
@upd_ctx('body', 'ct')
def render_json(dump_fields, **ctx):
    return dumps(dict([
        (field, ctx[field])
        for field in dump_fields
        if field in ctx
    ])),'text/plain'


@upd_ctx('response')
def response(body=None, ct='text/html', **ctx):
    code = 202 if body else 404
    return Response(body or "Nani-Nani", status=code, content_type=ct)

@upd_ctx('url', 'mime')
def route(request, **ctx):
    mime_set = set([
        mt
        for mt,prio in request.accept_mimetypes
    ])
    return request.path, mime_set, handlers

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
        dump_tpl,
        render_json,
        render_html,
        gen_by,

        view("/plain")([
            blog_posts,
            load_links,
            splash,
        ]),
        view('/')([
            blog_posts,
            load_links,
            splash,
        ]),
]

@Request.application
def application(request):
    ret = chain.run([route, response], request=request)
    return ret['response']

if __name__ == '__main__':
    from werkzeug.serving import run_simple
    run_simple('0.0.0.0', 4000, application)
