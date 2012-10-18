
from wsgiref.simple_server import make_server
from cgi import parse_qs, escape

import sb.util as util

import os
import shutil
import glob

# Should contain Makefile.{common,rules,example},
# with python calls written as $(PYTHON)
MAKEFILE_DIR = os.environ.get('MAKEFILE_DIR', '/home/dan/annotate/pipeline')

# Where to host the pipeline
PIPELINE_DIR = os.environ.get('PIPELINE_DIR', '/dev/shm/pipeline')

def make_hash(text):
    import hashlib
    return hashlib.sha1(text).hexdigest()

def pipeline(text, fmt):
    text_hash = make_hash(text)
    util.log.info('%s: "%s"', text_hash, text)

    text_dir = os.path.join(PIPELINE_DIR, text_hash)
    original_dir = os.path.join(text_dir, 'original')
    util.system.make_directory(original_dir)
    annotations_dir = os.path.join(text_dir, 'annotations')
    export_dir = os.path.join(text_dir, 'export')

    shutil.copyfile(os.path.join(PIPELINE_DIR, 'Makefile.example'),
                    os.path.join(text_dir, 'Makefile'))
    text_file = os.path.join(original_dir, 'text.xml')
    if os.path.isfile(text_file):
        util.log.info("File exists and is not rewritten: %s", text_hash)
    else:
        f = open(text_file, 'w')
        f.write('<text>' + text + '</text>')
        f.close()

    if fmt == 'vrt':
        util.system.call_binary('make', ['vrt', '-C', text_dir], verbose=True)

        vrt_file = os.path.join(annotations_dir, 'text.vrt')
        f = open(vrt_file, 'r')
        vrt = f.read()
        f.close()

        return vrt
    else:
        util.system.call_binary('make', ['export', '-C', text_dir], verbose=True)

        xml_file = os.path.join(export_dir, 'text.xml')
        f = open(xml_file, 'r')
        xml = f.read()
        f.close()

        return xml

def pipeline_prepare(socket_file):
    util.system.make_directory(PIPELINE_DIR)
    for f in glob.glob(os.path.join(MAKEFILE_DIR, 'Makefile.*')):
        shutil.copy(f, PIPELINE_DIR)
    os.environ['PYTHON']='catalaunch %s' % socket_file

def start_server(socket_file, hostname='localhost', port=8051):

    def serve(environ, start_response):
        try:
            request_body_size = int(environ.get('CONTENT_LENGTH', 0))
        except ValueError:
            request_body_size = 0

        query_dict = parse_qs(environ['QUERY_STRING'])

        text = query_dict.get('text', [''])[0]
        fmt = query_dict.get('fmt', ['xml'])[0]

        util.log.info("Running pipeline with text: %s", text)

        response_body = pipeline(text, fmt)

        status = '200 OK'
        response_headers = [('Content-Type', 'text/plain'),
                            ('Content-Length', str(len(response_body)))]

        start_response(status, response_headers)
        return [response_body]

    httpd = make_server(hostname, int(port), serve)

    pipeline_prepare(socket_file)

    httpd.serve_forever()

if __name__ == '__main__':
    util.run.main(start_server)
