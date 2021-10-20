import signalfx
import argparse
import json
import logging
import os
import re
import sys

from jinja2 import Environment, FileSystemLoader, Template

sys.path.insert(0, '/Users/corywatson/src/signalfx-python')


TIME_COLORS = [

    'gray',
    'blue',
    'azure',
    'navy',
    'brown',
    'orange',
    'yellow',
    'iris',
    'magenta',
    'pink',
    'purple',
    'violet',
    'lilac',
    'emerald',
    'green',
    'aquamarine',
    'red',
    'gold',
    'greenyellow',
    'chartreuse',
    'jade'
]
COLORS = [
    'gray',
    'blue',
    'light_blue',
    'navy',
    'dark_orange',
    'orange',
    'dark_yellow',
    'magenta',
    'cerise',
    'pink',
    'violet',
    'purple',
    'gray_blue',
    'dark_green',
    'green',
    'aquamarine',
    'red',
    'yellow',
    'vivid_yellow',
    'light_green',
    'lime_green'
]


def do_chart(client, chartId, name, chart_iter):
    # print('do chart info:', client, chartId, name)
    c = client.get_chart(chartId)
    fmt_name = re.sub(r'\W', '_', c['name']).lower()
    c['fmt_name'] = fmt_name + chart_iter
    c['terraformName'] = name
    if c['options']['type'] == 'TimeSeriesChart':
        return do_time_chart(client, c)
    elif c['options']['type'] == 'List':
        return do_list_chart(client, c)
    elif c['options']['type'] == 'SingleValue':
        return do_single_value_chart(client, c)
    elif c['options']['type'] == 'Text':
        return do_text_chart(client, c)
    # elif c['options']['type'] == 'TimeSeriesChart':
    #     print(c)
    #     do_list_chart(client, c, name)
    else:
        return c['options']['type']


def resolve_color(index):
    return COLORS[index]


def resolve_time_color(index):
    return TIME_COLORS[index]


def do_text_chart(client, chart):
    return text_chart_template.render(chart)


def do_list_chart(client, chart):
    return list_chart_template.render(chart)


def do_single_value_chart(client, chart):
    return single_value_chart_template.render(chart)


def do_dashboard(client, dashboardId, name):
    d = client.get_dashboard(dashboardId)
    d['terraformName'] = name
    new_charts = []
    chart_iter = 0
    for chart in d['charts']:
        new_charts.append(
            do_chart(client, chart['chartId'], name, str(chart_iter)))
        c = client.get_chart(chart['chartId'])
        fmt_name = re.sub(r'\W', '_', c['name']).lower()
        fmt_chart_type = re.findall(
            '[A-Z][^A-Z]*', c['options']['type'])[0].lower()
        if fmt_chart_type == 'single':
            fmt_chart_type = 'single_value'
        c['fmt_name'] = fmt_name + str(chart_iter)
        chart_full_id = 'signalfx_' + fmt_chart_type + \
            '_chart.' + c['fmt_name'] + '.id'
        chart['chart_full_id'] = chart_full_id
        chart_iter += 1
    d['newCharts'] = new_charts
    print(dashboard_template.render(d))


def do_detector(client, detectorId, name):
    d = client.get_detector(detectorId)
    d['terraformName'] = name
    print(detector_template.render(d))


def do_time_chart(client, chart):
    # print(chart)

    return time_chart_template.render(chart)
    # sys.exit(1)


parser = argparse.ArgumentParser()

parser.add_argument('--realm', help='SignalFx Realm (defaults to none)')
parser.add_argument('--verbose', help='Be verbose',
                    action='store_const', const=True)
parser.add_argument('--chart', help='A chart to convert')
parser.add_argument('--dashboard', help='A dashboard to convert')
parser.add_argument('--detector', help='A detector to convert')
parser.add_argument(
    '--name', help='Terraform name of resulting asset', required=True)

args = parser.parse_args()
if args.verbose:
    logging.basicConfig(level=logging.DEBUG)

if 'SFX_AUTH_TOKEN' not in os.environ:
    logging.error('ERROR: Please specify an SFx auth token via SFX_AUTH_TOKEN')
    sys.exit(1)
sfx_api_key = os.environ['SFX_AUTH_TOKEN']

templateLoader = FileSystemLoader(searchpath="./")
env = Environment(loader=templateLoader, trim_blocks=True, lstrip_blocks=True)

single_value_chart_template = env.get_template(
    'single_value_chart_template.tf.j2')
dashboard_template = env.get_template('dashboard_template.tf.j2')
detector_template = env.get_template('detector_template.tf.j2')
list_chart_template = env.get_template('list_chart_template.tf.j2')
time_chart_template = env.get_template('time_chart_template.tf.j2')
text_chart_template = env.get_template('text_chart_template.tf.j2')

if args.chart is None and args.dashboard is None and args.detector is None:
    sys.exit('Please supply a chart, dashboard, or detector ID to export')

if __name__ == "__main__":
    sfx = signalfx.SignalFx()
    if args.realm is not None:
        # Use a realm if we get one
        sfx = signalfx.SignalFx(
            api_endpoint='https://api.' + args.realm + '.signalfx.com')

    with sfx.rest(sfx_api_key) as rest:
        def do_chart_template(chartId, name):
            do_chart(rest, chartId, name)

        env.globals.update(do_chart=do_chart_template)
        env.globals.update(resolve_color=resolve_color)
        env.globals.update(resolve_time_color=resolve_time_color)

        if args.chart:
            do_chart(rest, args.chart, args.name)
        elif args.dashboard:
            do_dashboard(rest, args.dashboard, args.name)
        elif args.detector:
            do_detector(rest, args.detector, args.name)
