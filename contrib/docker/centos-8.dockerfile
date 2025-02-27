#
# Copyright (C) 2019 by frePPLe bv
#
# This library is free software; you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation; either version 3 of the License, or
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero
# General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public
# License along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

#
# STAGE 1: Compile and build the application
#

FROM centos:8 as builder

RUN yum -y update
RUN yum -y install dnf-plugins-core epel-release && \
  dnf config-manager --set-enabled powertools && \
  yum -y install xerces-c python36 git wget rpm-build \
    python3-psycopg2 python3-pip postgresql-devel openssl openssl-devel \
    cmake make python3-devel xerces-c-devel gcc-c++ python3-sphinx && \
  yum clean all 

# An alternative to the copy is to clone from git:
# RUN git clone https://github.com/frepple/frepple.git frepple
COPY frepple-*.tar.gz ./

RUN src=`basename --suffix=.tar.gz frepple-*` && \
  tar -xzf *.tar.gz && \
  rm *.tar.gz && \
  cd $src && \
  python3 -m pip upgrade pip && \
  python3 -m pip install -r requirements.txt && \
  mkdir build && \
  cd build && \
  cmake .. && \
  cmake --build . --target package

FROM scratch as package
COPY --from=builder frepple-*/build/*.rpm .

#
# STAGE 2: Build the deployment container
#

FROM centos:8

COPY --from=builder /frepple-*/requirements.txt .
COPY --from=builder /frepple-*/build/*.rpm .

RUN yum -y update && \
  yum -y install xerces-c python36 httpd python3-mod_wsgi \
     python3-psycopg2 python3-pip openssl postgresql-client && \
  yum clean all

RUN yum -y --no-install-recommends install \
  libxerces-c3.2 apache2 libapache2-mod-wsgi-py3 \
  python3-wheel ssl-cert python3-setuptools python3-psycopg2 python3-pip postgresql-client && \
  rpm -i frepple_*.rpm && \
  pip3 install -r requirements.txt && \
  a2enmod expires && \
  a2enmod wsgi && \
  a2enmod ssl && \
  a2ensite default-ssl && \
  a2ensite frepple && \
  service apache2 restart && \
  rm requirements.txt *.rpm && \
  yum -y remove python3-wheel python3-setuptools python3-pip

EXPOSE 80
EXPOSE 443

VOLUME ["/var/log/frepple", "/etc/frepple", "/var/log/apache2", "/etc/apache2"]

# Update djangosettings
# TODO update random secret key
RUN sed -i 's/"HOST": ""/"HOST": "frepple-postgres"/g' /etc/frepple/djangosettings.py

CMD frepplectl migrate && \
  rm -f /usr/local/apache2/logs/httpd.pid && \
  apachectl -DFOREGROUND
