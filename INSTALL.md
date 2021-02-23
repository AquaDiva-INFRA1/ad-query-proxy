# Setting up the query proxy

These instructions assume that you will set up the proxy on a remote machine.

Before you get started, you should have set up login via ssh.

```bash
ssh-copy-id user@example.com
```

## Setting up [Ansible](https://docs.ansible.com/ansible/latest/installation_guide/intro_installation.html#virtual-environments)*

Create a virtual environment for Ansible.

```bash
python3 -m venv ansible
source ansible/bin/activate
python3 -m pip install ansible
ansible-galaxy install elastic.elasticsearch,7.11.1
ansible-galaxy collection install community.general
```

Make sure the ansible_host variable in scripts/ansible/hosts is set correctly and execute the playbook from scripts/ansible/es-proxy.yml:

```
ansible-playbook es-proxy.yml --ask-become-pass -i hosts
```

You can then deactivate the virtual environment again.

```bash
deactivate
```

Ansible will then log into the client to install [Elasticsearch](https://www.elastic.co/elasticsearch/)**, the Mapper [Annotated Text](https://www.elastic.co/blog/search-for-things-not-strings-with-the-annotated-text-plugin) [plugin](https://www.elastic.co/guide/en/elasticsearch/plugins/current/mapper-annotated-text.html) for Elasticsearch, as well as setup Elasticsearch as a service, so that it will be restarted, if the machine needs to be restarted for maintenance or other reasons.

### Details of the es-proxy.yml playbook

```yaml
- name: Setup Elasticsearch query proxy
  hosts: es-proxy
  become: True
```
"hosts" refers to the 'hosts' file, where the hostname, username and additional settings like the [Python interpreter](https://docs.ansible.com/ansible/latest/reference_appendices/python_3_support.html#using-python-3-on-the-managed-machines-with-commands-and-playbooks) to use (*e.g.* /usr/bin/python3) are stored.

"become: True" lets Ansible become a superuser for the duration of the playbook. This is necessary to install Elasticsearch as a system-wide service.

```yaml
  roles:
  - role: elastic.elasticsearch
  vars:
    es_version: 7.11.1
```

[Roles](https://docs.ansible.com/ansible/latest/user_guide/playbooks_reuse_roles.html) let you bundle up and distribute tasks. [Elastic](https://github.com/elastic/ansible-elasticsearch) provides an Ansible role for easy deployment of an Elasticsearch service.

```yaml
  tasks:
  - name: Remove previous installations of Mapper Annotated Text plugin
    community.general.elasticsearch_plugin:
      name: mapper-annotated-text
      state: absent
      
  - name: Install Mapper Annotated Text plugin in Elasticsearch
    community.general.elasticsearch_plugin:
      name: mapper-annotated-text
      state: present
      version: 7.11.1
```

The query proxy relies on the [Mapper Annotated Text plugin](https://www.elastic.co/blog/search-for-things-not-strings-with-the-annotated-text-plugin) that got introduced in Elasticsearch [6.5](https://www.elastic.co/guide/en/elasticsearch/plugins/6.5/mapper-annotated-text.html) and carries on to be supported in [7.11](https://www.elastic.co/guide/en/elasticsearch/plugins/7.11/mapper-annotated-text.html). Still, the plugin is considered 'experimental' and might get changed or removed in the future. Please read version notes carefully with regard to that.

In case of updates to the system, it is important that the plugin is removed first. Otherwise Elasticsearch will complain about incompatible versions between the search engine and the plugin, as newer versions of the plugin won't get installed. The install process will only check, if the plugin is already present, regardless of its version.

```yaml
  - name: Enable service elasticsearch
    systemd:
      name: elasticsearch
      daemon-reload: yes
      enabled: yes
    notify: restart machine
```

To make sure that Elasticsearch is up and running, we explicitly enable the service and (re-)start Elasticsearch.

```yaml
  - name: Prevent Elasticsearch from being upgraded
    dpkg_selections:
      name: elasticsearch
      selection: hold
```

This entry is important to avoid version conflicts between the Mapper Annotated Text plugin and Elasticsearch itself. Without it, it would be possible that the package manager of the operating system (apt) considers Elasticsearch to be eligible for an update. Getting the versions of them out if sync would cause Elasticsearch to fail starting up the search engine.

Instead, apt will issue the following message:

```bash
The following packages have been kept back:
  elasticsearch
```

```yaml
  - name: Install curl
    apt:
      name: curl
      update_cache: yes
```

This package is not strictly necessary and only included for testing purposes. It enables you to send queries to the web server, if you want to inspect the raw response.

```yaml
  handlers:
  - name: restart machine
    service: name=elasticsearch state=restarted
```

waitress-serve --port=8081 --call 'query_proxy.flask_main:wsgi'

*Ansible is a registered trademark of Red Hat, Inc. in the United States and other countries.
**Elasticsearch is a trademark of Elasticsearch BV, registered in the U.S. and in other countries.

## Get the proxy ready to serve documents

After logging in to the machine (and perhaps setting up a virtual environment), download the project files and install all of its dependencies.

```bash
git clone https://github.com/JULIELab/ad-query-proxy.git
cd ad-query-proxy
python -m pip install -r requirements.txt
```

Be sure that the ontology you want to use has also been transferred to the machine. The rest of the work can be done in 5 lines.

### 1. Create a new dictionary tagger

1. Download a copy of the NCBI Taxonomy, as preprocessed by the EBI:

```
wget ftp://ftp.ebi.ac.uk/pub/databases/taxonomy/taxonomy.dat
```

2. Combine your ontology with the matching entries of the NCBI Taxonomy and write a dictionary tagger to disk:

```python
python -m preprocessing.onto2trie --input ../ad-ontology.owl --ncbi taxonomy.dat --output ad-tagger.pickle
```

### 2. Index the PubMed/MEDLINE baseline

You can then use the dictionary tagger to populate a search index with processed PubMed/MEDLINE documents:

```bash
mkdir temp
python -m query_proxy.ncbi temp ad-tagger.pickle&
```

As the Python process will take a long time to index all available baseline documents, it is best to start it in the background. Starting it in a terminal multiplexer is also highly recommended.

### 3. Start a web server

```bash
waitress-serve --port=8080 --call 'query_proxy.flask_main:wsgi'
```

Ready!