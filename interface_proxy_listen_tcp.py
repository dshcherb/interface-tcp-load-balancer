import json

from ops.framework import Object, StoredState, EventBase, EventsBase, EventSource


class BackendsChanged(EventBase):
    pass


class InterfaceProvidesEvents(EventsBase):
    backends_changed = EventSource(BackendsChanged)


class ListenProxyData:

    def __init__(self, section_name, listen_options, server_options):
        self.section_name = section_name
        self.listen_options = listen_options
        self.server_options = server_options


class ProxyListenTcpInterfaceRequires(Object):

    on = InterfaceProvidesEvents()

    state = StoredState()

    def __init__(self, charm, relation_name):
        super().__init__(charm)
        self._relation_name = relation_name
        self._listen_proxies = None
        self.framework.observe(charm.on[relation_name].changed, self.on_changed)

    def on_changed(self, event):
        self.on.backends_changed.emit()

    @property
    def listen_proxies(self):
        if self._listen_proxies is None:
            self._listen_proxies = []
            for relation in self.model.relations[self._relation_name]:
                app_data = relation.data[relation.app]
                listen_options = json.loads(app_data.get('listen_options', '[]'))
                listen_options.append('mode tcp')
                server_options = []
                for unit in relation.units:
                    server_option = relation.data[relation.unit].get('server_option')
                    if server_option is not None:
                        server_options.append(server_option)

                section_name = f'{relation.name}_{relation.id}_{relation.app.name}'
                self._listen_proxies.append(
                    ListenProxyData(section_name, listen_options, server_options))
        return self._listen_proxies


class ProxyListenTcpInterfaceProvides(Object):

    def __init__(self, charm, relation_name):
        super().__init__(charm)
        self._relation_name
        # TODO: there could be multiple independent reverse proxies in theory, address that later.
        self._relation = self.model.get_relation(relation_name)

    def expose_server(self, listen_options, server_option):
        # Expose common settings via app relation data from a leader unit.
        if self.model.unit.is_leader():
            app_data = self._relation.data[self.model.app]
            app_data['listen_options'] = json.dumps(listen_options)
        self._relation.data[self.model.unit]['server_option'] = server_option
