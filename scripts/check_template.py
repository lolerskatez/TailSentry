import jinja2
import traceback
import sys

env = jinja2.Environment(loader=jinja2.FileSystemLoader('templates'))
try:
    env.get_template('faq.html')
    print('TEMPLATE OK')
except Exception:
    traceback.print_exc()
    sys.exit(1)
