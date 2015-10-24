from jinja2 import Environment, PackageLoader

from gitinspector_plus.renderers.base import BaseRenderer


class HTMLRenderer(BaseRenderer):

    def __init__(self):
        self.jinja_env = Environment(loader=PackageLoader('gitinspector_plus', 'templates'))

    def render_commit_statistics(self, repo_stats):
        template = self.jinja_env.get_template('index.html')
        print template.render()
