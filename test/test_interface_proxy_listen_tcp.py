#!/usr/bin/env python3

import unittest

from ops.charm import CharmBase

from ops.testing import Harness
from interface_proxy_listen_tcp import ProxyListenTcpInterfaceRequires


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
        self.assertEqual(self.tcp_backends.listen_proxies[0].server_options,
                         ['server tcp-server-1.example 192.0.2.3:26257 check port 8080',
                          'server tcp-server-0.example 192.0.2.2:26257 check port 8080'])
        self.assertEqual(self.tcp_backends.listen_proxies[0].section_name,
                         'proxy-listen-tcp_0_tcp-server')


if __name__ == "__main__":
    unittest.main()
