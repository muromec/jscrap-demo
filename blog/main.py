import os
from werkzeug.wrappers import Request, Response
from simplejson import dumps
from biribiri import chain
from biribiri.chain.utils import upd_ctx, view, match
from jinja2 import Environment, FileSystemLoader

"""
Ok, whats going on here?

First, look at entry point, called "application"
"""


@Request.application
def application(request):
    """
    Typical werkzeug app, nothing special.

    Here I`m handling incoming request and passing it to
    chain of functions (route, response).

    Execution context is almost empty, except our request.

    """

    ret = chain.run([route, response], request=request)
    return ret['response']

@upd_ctx('url', 'mime')
def route(request, **ctx):
    """
    This function called route.

    Really it just grabs some data from request and puts
    back into execution context as variables "url" 
    and "mime".

    This is the meaning of @upd_ctx - update context with
    values, returned from function.

    First one is relative url and mime is set of all
    mime-types, browser claimed to understand.

    Url used to route request into specific @view
    and "mime" used to determine, how execution
    context would be rendered back to user

    And the most important part is last: handlers list.
    Handlers list may look like url map, but it`s not one.

    Url mapper selects just *one* function to handle url,
    handlers list specifies *many* functions, calling
    one by one. Really, it calls *every* function in
    handlers list, but some are filtered out by decorators.
    """

    mime_set = set([
        mt
        for mt,prio in request.accept_mimetypes
    ])
    return request.path, mime_set, handlers


def f(filename, f=__file__, sep=""):
    """
    Dont mind me, I`m just a helper function
    to find, where my templates are
    """
    path,_file = os.path.split(f)
    return os.path.join(path, sep, filename)

env = Environment( loader=FileSystemLoader( 
    [ f("templates") ]
))

def accept(*know_mime):
    """
    Here is simple decorator, choosing which
    render function to run.

    Using request.args is a bit of hack, as browsers
    are not smart enought to tell me, what they want

    Look, its not *running* function, but returning
    it same way, as "route" returns handlers list
    """
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
    """
    This function selects template used to render
    page and list of context variables which are
    safe to dump to user in json request

    How this functon called? Look at handlers list.
    
    """
    return 'splash.html', [ 'nav', 'gen', 'post_list', 'url',],None

@upd_ctx('nav')
def load_links(**ctx):
    """
    I`m lazy. No real database here, just hardcoded result.

    All this vars are availiable inside template.
    """
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
    """
    Same as above, adding data to context to catch it back
    inside template.
    """
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
    """
    Add text to footer
    """
    import jinja2
    return "Jinja %s" % jinja2.__version__

@accept('text/javascript', 'js')
@upd_ctx('body', 'ct')
def dump_tpl(tpl, **ctx):
    """
    Here I`m compiling template into js code
    and dumping it to browser.

    Template selected by function "splash" which is 
    view function for "/".

    This handler called every time, somebody GETs /?js
    """
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
    """
    Wow, browser is smart enough to understand HTML!

    Renderig whole context for such case.

    Template name selected by "splash"
    """
    tpl_o = env.get_template(tpl)

    return tpl_o.render(**ctx)

@accept('json')
@match(dump_fields=list)
@upd_ctx('body', 'ct')
def render_json(dump_fields, **ctx):
    """
    Somebody called  /?json. Ok, dump it.

    Its same context, as in every "/" call, but
    result consists of safe vars, serilized to json.
    """
    return dumps(dict([
        (field, ctx[field])
        for field in dump_fields
        if field in ctx
    ])),'text/plain'


@upd_ctx('response')
def response(body=None, ct='text/html', **ctx):
    """
    Nothing interesting. If somebody pushed "body" 
    into context, return it. If nothing it`s 404.
    """
    code = 202 if body else 404
    return Response(body or "Nani-Nani", status=code, content_type=ct)

@match(found_view=None, body=None)
@upd_ctx('body')
def static(url, **ctx):
    """
    I should call special people to configure nginx.

    Dont serve static in this way!
    """
    if not url.startswith('/static'):
        # yeah, this is ugly!
        return

    _,static,package,path = url.split('/',3)
    if package not in ['jscrap', 'blog']:
        return

    mod = __import__(package)
    try:
        return open(f(path, mod.__file__, 'data'), 'rb')
    except IOError:
        return

"""
Here is handlers list.

Functins called from down to up.


"""
handlers = [
        static,
        dump_tpl,    # one of this three should render
        render_json, # body into something
        render_html, # readable by browser.
        gen_by,

        view("/plain")([
            blog_posts,
            load_links,
            splash,
        ]),
        view('/')([
            # Every function in this block called
            # to render splash template.
            #
            # Again. From bottom to top.
            blog_posts,
            load_links,
            splash,
        ]),
]

if __name__ == '__main__':
    from werkzeug.serving import run_simple
    run_simple('0.0.0.0', 4000, application)
