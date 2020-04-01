#!/usr/bin/env python3

import unittest

from ops.charm import CharmBase

from ops.testing import Harness
from interface_proxy_listen_tcp import (
    ProxyListenTcpInterfaceRequires,
    ProxyListenTcpInterfaceProvides
)


class TestProxyListenTcpInterfaceRequires(unittest.TestCase):

    def setUp(self):
        self.harness = Harness(CharmBase, meta='''
            name: haproxy
            requires:
              proxy-listen-tcp:
                interface: proxy-listen-tcp
        ''')

        self.harness.begin()
        self.tcp_backends = ProxyListenTcpInterfaceRequires(self.harness.charm, 'proxy-listen-tcp')

    def test_listen_proxies(self):
        relation_id = self.harness.add_relation('proxy-listen-tcp', 'tcp-server')
        self.harness.update_relation_data(
            relation_id, 'haproxy/0', {'ingress-address': '192.0.2.1'})

        self.harness.add_relation_unit(
            relation_id, 'tcp-server/0', {
                'ingress-address': '192.0.2.2',
                'server_option': 'server tcp-server-0.example 192.0.2.2:26257 check port 8080'
            })
        self.harness.add_relation_unit(
            relation_id, 'tcp-server/1', {
                'ingress-address': '192.0.2.3',
                'server_option': 'server tcp-server-1.example 192.0.2.3:26257 check port 8080'
            })
        self.harness.update_relation_data(relation_id, 'tcp-server', {
            'frontend_port': "26257",
            'listen_options': '["bind :26257", "option httpchk GET /health?ready=1"]'
        })

        self.assertEqual(self.tcp_backends.listen_proxies[0].listen_options,
                         ['bind :26257', 'option httpchk GET /health?ready=1', 'mode tcp'])
        self.assertEqual(set(self.tcp_backends.listen_proxies[0].server_options),
                         set(['server tcp-server-0.example 192.0.2.2:26257 check port 8080',
                              'server tcp-server-1.example 192.0.2.3:26257 check port 8080']))
        self.assertEqual(self.tcp_backends.listen_proxies[0].section_name,
                         'proxy-listen-tcp_0_tcp-server')

    def test_frontend_ports(self):
        relation_id_a = self.harness.add_relation('proxy-listen-tcp', 'tcp-server-a')
        relation_id_b = self.harness.add_relation('proxy-listen-tcp', 'tcp-server-b')

        self.harness.update_relation_data(
            relation_id_a, 'haproxy/0', {'ingress-address': '192.0.2.1'})

        self.harness.update_relation_data(relation_id_a, 'tcp-server-a', {
            'frontend_port': "26257",
        })
        self.harness.update_relation_data(relation_id_b, 'tcp-server-b', {
            'frontend_port': "26258",
        })

        self.assertEqual(self.tcp_backends.frontend_ports, [])

        self.harness.add_relation_unit(
            relation_id_a, 'tcp-server-a/0', {
                'ingress-address': '192.0.2.2',
                'server_option': 'server tcp-server-0.example 192.0.2.2:26257 check port 8080'
            })
        self.harness.add_relation_unit(
            relation_id_b, 'tcp-server-b/0', {
                'ingress-address': '192.0.2.3',
                'server_option': 'server tcp-server-1.example 192.0.2.3:26257 check port 8080'
            })

        self.assertEqual(self.tcp_backends.frontend_ports, ['26257', '26258'])


class TestProxyListenTcpInterfaceProvides(unittest.TestCase):

    def setUp(self):
        self.harness = Harness(CharmBase, meta='''
            name: tcp-server
            requires:
              proxy-listen-tcp:
                interface: proxy-listen-tcp
        ''')

        self.harness.begin()
        self.tcp_load_balancer = ProxyListenTcpInterfaceProvides(self.harness.charm,
                                                                 'proxy-listen-tcp')

    def test_expose_server(self):
        relation_id = self.harness.add_relation('proxy-listen-tcp', 'tcp-server')
        self.harness.update_relation_data(
            relation_id, 'tcp-server/0', {'ingress-address': '192.0.2.1'})

        self.tcp_load_balancer.expose_server(
            26257,
            ["bind :26257", "option httpchk GET /health?ready=1"],
            'server tcp-server-0.example 192.0.2.1:26257 check port 8080'
        )

        rel = self.harness.charm.model.get_relation('proxy-listen-tcp')
        self.assertEqual(
            rel.data[self.harness.charm.unit]['server_option'],
            'server tcp-server-0.example 192.0.2.1:26257 check port 8080'
        )
        with self.assertRaises(KeyError):
            rel.data[self.harness.charm.app]['frontend_port']
        with self.assertRaises(KeyError):
            rel.data[self.harness.charm.app]['listen_options'],

        self.harness.set_leader()
        self.tcp_load_balancer.expose_server(
            26258,
            ["bind :26258", "option httpchk GET /health?ready=1"],
            'server tcp-server-0.example 192.0.2.1:26258 check port 8080'
        )
        self.assertEqual(
            rel.data[self.harness.charm.unit]['server_option'],
            'server tcp-server-0.example 192.0.2.1:26258 check port 8080'
        )
        self.assertEqual(rel.data[self.harness.charm.app]['frontend_port'], '26258')
        self.assertEqual(
            rel.data[self.harness.charm.app]['listen_options'],
            '["bind :26258", "option httpchk GET /health?ready=1"]'
        )


if __name__ == "__main__":
    unittest.main()
