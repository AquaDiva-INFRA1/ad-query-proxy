# Setting up the query proxy

ssh-copy-id user@example.com

## Setting up [Ansible](https://docs.ansible.com/ansible/latest/installation_guide/intro_installation.html#virtual-environments)*

```bash
python3 -m venv ansible
source ansible/bin/activate
python3 -m pip install ansible
ansible-galaxy install elastic.elasticsearch,7.9.2  #
ansible-galaxy collection install community.general
```

```
ansible-playbook es-proxy.yml --ask-become-pass -i hosts
```

Ansible will then log into the client to install [Elasticsearch](https://www.elastic.co/elasticsearch/)**, the Mapper [Annotated Text](https://www.elastic.co/blog/search-for-things-not-strings-with-the-annotated-text-plugin) [plugin](https://www.elastic.co/guide/en/elasticsearch/plugins/current/mapper-annotated-text.html) for Elasticsearch, as well as setup Elasticsearch as a service, so that it will be restarted, if the machine needs to be restarted for maintenance or other reasons.

```
deactivate
```

*Ansible is a registered trademark of Red Hat, Inc. in the United States and other countries.
**Elasticsearch is a trademark of Elasticsearch BV, registered in the U.S. and in other countries.