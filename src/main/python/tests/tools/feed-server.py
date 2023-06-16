import functools
import http.server
import os


def serve_feeds():
    handler = functools.partial(
        http.server.SimpleHTTPRequestHandler,
        directory=os.path.join(os.path.dirname(__file__), "feeds")
    )
    server = http.server.HTTPServer(('', 8000), handler)
    try:
        print("Serving feeds on port 8000")
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    serve_feeds()
