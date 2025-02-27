#
# Copyright (C) 2018-2019 by frePPLe bv
#
# This library is free software; you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
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

FROM opensuse/leap:15.1 as builder

RUN zypper refresh && \
  zypper --non-interactive update && \
  zypper --non-interactive install --force-resolution --replacefiles \
    libxerces-c-3_1 httpd python3 python3-pip python3-psycopg2 gcc rpmbuild \
    libxerces-c-devel openssl cmake python3-devel gcc-c++ gcc tar gzip \
    libpq5 postgresql-devel postgresql openssl-devel && \
  pip3 install sphinx && \
  zypper clean

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

FROM opensuse/leap:15.1

RUN zypper refresh && \
  zypper --non-interactive update && \
  zypper --non-interactive install --force-resolution --replacefiles \
    libxerces-c-3_1 openssl httpd apache2-mod_wsgi-python3 python3 gcc \
    python3-devel python3-pip libpq5 python3-psycopg2 postgresql && \
  zypper clean

COPY --from=builder frepple-*/build/requirements.txt ./
COPY --from=builder frepple-*/build/*.rpm ./

RUN rpm -i frepple*.rpm && \
  pip3 install -r requirements.txt && \
  a2enmod proxy && \
  a2enmod proxy_wstunnel && \
  rm requirements.txt *.rpm

EXPOSE 80
EXPOSE 443

VOLUME ["/var/log/frepple", "/etc/frepple", "/var/log/apache2", "/etc/apache2"]

# Update djangosettings
# TODO update random secret key
RUN sed -i 's/"HOST": ""/"HOST": "frepple-postgres"/g' /etc/frepple/djangosettings.py

CMD frepplectl migrate && \
  rcapache2 start && \
  tail -f /var/log/apache2/*log


