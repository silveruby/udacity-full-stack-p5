Name: Udacity Project 5

Description: Deploy webapp for the Udacity training course.

---

## 1. IP address and SSH port

1. Download private key
	
2. Move private key to home directory .ssh
		
		$ mv ~/Downloads/udacity_key.rsa ~/.ssh/
	
3. Update permission
	
		$ chmod 600 ~/.ssh/udacity_key.rsa
		
4. Login as grader via port 2200
	
		$ ssh -i ~/.ssh/udacity_key.rsa grader@52.34.126.189 -p 2200

5. URL for web app

		http://52.34.126.189/

## 2. Installation and configuration
	
1. Update OS software
	
		$ sudo apt-get update
		$ sudo apt-get upgrade

2. Add user grader (Source: [digitalocean][adduser], [askubuntu][visudo], [udacity][login])
	
	2.1 Add user
	
		$ sudo adduser grader
		$ sudo visudo			
		
		Add the following line after '# User privilege specification'
		
		grader ALL=(ALL:ALL) NOPASSWD:ALL	
		
	2.3 Copy public key from root to grader
	
		$ cd /home/grader
		$ sudo mkdir .ssh
		$ cd .ssh
		$ sudo mv /root/.ssh/authorized_keys .
		$ sudo chmod 755 authorized_keys
	
[adduser]: https://www.digitalocean.com/community/tutorials/how-to-add-and-delete-users-on-an-ubuntu-14-04-vps
[visudo]: http://askubuntu.com/questions/334318/sudoers-file-enable-nopasswd-for-user-all-commands
[login]: https://discussions.udacity.com/t/grader-login-not-working/29469/9

3. Change SSH port from 22 to 2200 (Source: [linuxlookup][sshport])

	3.1 Open ssh configuration file
	
		$ sudo vim /etc/ssh/sshd_config
		
		Update port from 22 to 2200
	
	3.2 Restart ssh server
	
		$ sudo service ssh restart
		
[sshport]: http://linuxlookup.com/howto/change_default_ssh_port

4. Setup firewall (Source: [ubuntu][firewall], [udacity][ufwport])

		$ sudo ufw default deny incoming
		$ sudo ufw default deny outgoing
		$ sudo ufw allow 2200/tcp
		$ sudo ufw allow 80/tcp
		$ sudo ufw allow 123/udp
		$ sudo ufw enable
		$ sudo ufw status
		
	**Note: ** When installing Apache, PostgreSQL, Git and other packages, make sure to disable ufw first or else we might get download errors. 

[firewall]: https://help.ubuntu.com/community/UFW
[ufwport]: https://www.udacity.com/course/viewer#!/c-ud299-nd/l-4331066009/m-4801089499

5. Change time zone to UTC (Source: [ubuntu][timezone])
		
		sudo dpkg-reconfigure tzdata

[timezone]: http://askubuntu.com/questions/138423/how-do-i-change-my-timezone-to-utc-gmt


6. Install Apache and WSGI (Source: [udacity][configlinux], [askubuntu][servername])

	6.1 Install Apache web server:
		
		$ sudo apt-get install apache2
		
	6.2 Install Python and mod_wsgi for serving Flask apps: 

		$ sudo apt-get install python-dev python-setuptools libapache2-mod-wsgi
		
	6.3 Get rid of ServerName error
	
		$ echo "ServerName HOSTNAME" | sudo tee /etc/apache2/conf-available/fqdn.conf
		$ sudo a2enconf fqdn
		
	6.3 Restart Apache server
	
		$ sudo service apache2 restart
		
[configlinux]: https://www.udacity.com/course/viewer#!/c-ud299-nd/l-4340119836/m-4818948614
[servername]: http://askubuntu.com/questions/256013/could-not-reliably-determine-the-servers-fully-qualified-domain-name

7. Deploy simple Flask app (Source: [digitalocean][flaskapp])

	7.1 Enable WSGI 
	
		$ sudo a2enmod wsgi
	
	7.2 Create a Flask app
	
		$ cd /var/www
		$ sudo mkdir catalog
		$ cd catalog
		$ sudo mkdir catalog
		$ cd catalog
		$ sudo mkdir static templates
		$ sudo vi __init__.py
		
		Copy & paste the follwing code into file:
		
		from flask import Flask
		app = Flask(__name__)
		@app.route("/")
		def hello():
		    return "Hello, I love penguins!"
		if __name__ == "__main__":
		    app.run()
		    
	7.3 Setup virtual environment & install Flask
	
		$ pwd
		
		Make sure we are in /var/www/catalog/catalog
		
		$ sudo apt-get install python-pip 
		$ sudo pip install virtualenv 
		$ sudo virtualenv venv
		$ sudo chmod -R 777 venv
		$ source venv/bin/activate 
		$ sudo pip install Flask
		
	7.4 Test run Flask app
	
		$ sudo python __init__.py 
		
		Install is successful if we see “Running on http://localhost:5000/” 
		or "Running on http://127.0.0.1:5000/"
		
		Then, deactive virtual environment
		
		$ deactivate
		
	7.5 Add virtual host configuration file
		
		$ sudo vi /etc/apache2/sites-available/catalog.conf
		
		Add the following code to file:
		
		<VirtualHost *:80>
			ServerName 52.34.126.189
			ServerAdmin zhengsan@gmail.com
			WSGIScriptAlias / /var/www/catalog/catalog.wsgi
			<Directory /var/www/catalog/catalog/>
				Order allow,deny
				Allow from all
			</Directory>
			Alias /static /var/www/catalog/catalog/static
			<Directory /var/www/catalog/catalog/static/>
				Order allow,deny
				Allow from all
			</Directory>
			ErrorLog ${APACHE_LOG_DIR}/error.log
			LogLevel warn
			CustomLog ${APACHE_LOG_DIR}/access.log combined
		</VirtualHost>	
		
	7.6 Enable virtual host
		
		$ sudo a2ensite catalog
		
	7.7 Create WSGI file
	
		$ cd /var/www/catalog
		$ sudo vi catalog.wsgi
		
		Add the following code to file:
		
		#!/usr/bin/python
		import sys
		import logging
		logging.basicConfig(stream=sys.stderr)
		sys.path.insert(0,"/var/www/catalog/")
		
		from catalog import app as application
		application.secret_key = 'Add your secret key'
		
	7.8 Restart Apache
	
		sudo service apache2 restart
	

[flaskapp]:https://www.digitalocean.com/community/tutorials/how-to-deploy-a-flask-application-on-an-ubuntu-vps

8. Install Git (Soure: [digialocean][installgit])
		
		$ sudo apt-get install git
		$ git config --global user.name "YOUR NAME"
		$ git config --global user.email "YOUR EMAIL ADDRESS"


[installgit]:https://www.digitalocean.com/community/tutorials/how-to-install-git-on-ubuntu-14-04

9. Replace catalog with code from github repository 

		$ cd /var/www/catalog
		$ sudo git clone https://github.com/silveruby/udacity-full-stack-p3.git
		$ sudo mv catalog catalog_old
		$ sudo mv udacity-full-stack-p3 catalog
		
10. Install packages required to run the project (Source: [flask-seasurf][seasurf], [oauth2client][oauth2client], [stueken][stueken])

		First, activate new virtual environment for catalog for for installs
		$ sudo virtualenv venv 
		$ sudo chmod -R 777 venv
		$ source venv/bin/activate
		
		Re-install Flask 
		$ sudo pip install Flask
		
		Install project dependencies
		$ sudo pip install httplib2
		$ sudo pip install dicttoxml
		$ sudo pip install flask-seasurf
		$ sudo pip install --upgrade oauth2client
		$ sudo pip install sqlalchemy
		$ sudo apt-get install python-psycopg2
		
[seasurf]:https://flask-seasurf.readthedocs.org/en/latest/
[oauth2client]:https://github.com/google/oauth2client
[stueken]:https://github.com/stueken/FSND-P5_Linux-Server-Configuration

11. Install PostgreSQL

		$ sudo apt-get install postgresql postgresql-contrib
		
		Make sure there's no remote connection to DB
		
		$ sudo less /etc/postgresql/9.3/main/pg_hba.conf

12. Create new PostgreSQL user (Source: [trackets][createdbuser], [postgresql][createdbuser2], [stueken][stueken])

		$ sudo -u postgres psql
		# CREATE USER catalog WITH PASSWORD 'catalog';
		# ALTER USER catalog CREATEDB; 
		
[createdbuser]:http://blog.trackets.com/2013/08/19/postgresql-basics-by-example.html
[createdbuser2]: http://www.postgresql.org/docs/8.0/static/sql-createuser.html

13. Create new PostgreSQL DB
		
		# CREATE DATABASE catalogdb WITH OWNER catalog;

		ctrl+D: Exit out of psql interactive mode 
		
14. Update SQLAlchemy engine parameters (Source: [sqlalchemy][engine])

		$ sudo vi database_setup.py	
		
		Update create engine parameter to the following:
		
		engine = create_engine('postgresql://catalog:catalog@localhost/catalogdb')
		
		$ sudo vi project.py
		
		Also update create engine parameter as you did for database_setup.py
		
		Rename project.py to __init__.py
		
		$ sudo mv project.py __init__.py
		
[engine]:http://docs.sqlalchemy.org/en/latest/core/engines.html

15. Initiate PostgreSQL DB

		$ sudo python database_setup.py
		
		Restart Apache server
	
		$ sudo service apache2 restart
		
16. Update all file relative paths to absolute paths in __init__.py

		fb_client_secrets.json to /var/www/catalog/catalog/fb_client_secrets.json
		authorized_users.json to /var/www/catalog/catalog/authorized_users.json

16. Add IP address to Facebook Valid OAuth redirect URIs
		
		IP address: http://52.34.126.189

