
## Windows based Alert Manager development with Docker

### 1. Setup Linux VM on Windows ###
Docker is a Linux-only virtual environment manager.  Windows developers that want to leverage Docker must setup a VM with a linux image.

Preflight Requirements

1. **Ensure to enable virtualization in BIOS:** (found under "security").  Virtualbox will not work without the Intel's virtualization features turned on
2. **Ensure you are HARD WIRED to your network:** Virtualbox does not come with drivers that handle wireless networking.

Install required software

1. Install [VirtualBox](http://www.oracle.com/technetwork/server-storage/virtualbox/downloads/index.html) (reboot required)
2. Install [Vagrant](https://www.vagrantup.com/downloads.html)
3. Install [Putty](http://www.chiark.greenend.org.uk/~sgtatham/putty/download.html) (select the putty-0.6x-installer.exe)

Vagrant is used to fill the VirtualBox VM with a Linux instance

4. Open a command prompt (```cmd.exe```) ensure you have adminstrator access
5. Find an enpty directory to place the vm and vagrant files. I am using ```c:\vms```


    <pre>vagrant init ubuntu/trusty64
    vagrant up
    </pre>

Vagrant will find your VirtualBox installation, make a VM instance, download
the ```ubuntu/trusty64``` image and start the instance.  Here is the output:

<pre>
    C:\vms&gt;vagrant init ubuntu/trusty64
    A `Vagrantfile` has been placed in this directory. You are now
    ready to `vagrant up` your first virtual environment! Please read
    the comments in the Vagrantfile as well as documentation on
    `vagrantup.com` for more information on using Vagrant.

    C:\vms&gt;vagrant up
    Bringing machine 'default' up with 'virtualbox' provider...
    ==&gt; default: Box 'ubuntu/trusty64' could not be found. Attempting to find and install...
        default: Box Provider: virtualbox
        default: Box Version: &gt;= 0
    ==&gt; default: Loading metadata for box 'ubuntu/trusty64'
        default: URL: https://atlas.hashicorp.com/ubuntu/trusty64
    ==&gt; default: Adding box 'ubuntu/trusty64' (v14.04) for provider: virtualbox
        default: Downloading: https://atlas.hashicorp.com/ubuntu/boxes/trusty64/versions/14.04/providers/virtualbox.box
        default: Progress: 52% (Rate: 947k/s, Estimated time remaining: 0:02:01))

    C:\vms&gt;"c:\Program Files\Oracle\VirtualBox\VBoxManage.exe" list runningvms
    "kyle_default_1418757660027_23403" {61ad6718-2e44-4a8e-9a25-49d138651833}
</pre>
Your VM is now running, but you must open another port to access the Alert Manager (once we get it installed):

6. In Virtualbox go to *Settings->Network->port Forwarding* and add a map from 127.0.0.1:8080 to 0.0.0.0:8080

### 2. Setup Putty on Windows ###

```vagrant ssh``` on the command line will not work, but it will give you the information required  to ssh in with Putty:

<pre>
    c:\vms&gt;vagrant ssh
    `ssh` executable not found in any directories in the %PATH% variable. Is an
    SSH client installed? Try installing Cygwin, MinGW or Git, all of which
    contain an SSH client. Or use your favorite SSH client with the following
    authentication information shown below:

    Host: 127.0.0.1
    Port: 2222
    Username: vagrant
    Private key: c:/vms/.vagrant/machines/default/virtualbox/private_key
</pre>

Please note that Vagrant created a (unsecure) private key in ```c:\vms\.vagrant\machines\default\virtualbox\private_key```.  You must convert that key to something Putty can use.

7.  open puttyGen, load the ```private_key``` and save it as ```private_key.ppk```

Open Putty and fill out the seesion and connection parameters using the GUI.  They are scattered throughout the menu, so I listed the paths to

* Session->host name = 127.0.0.1
* Session->port 2222
* Connection->data->auto login username = vagrant
* Connection->SSH->Auth-> private key file for authentication = c:\vms\.vagrant\machines\default\virtualbox\private_key.ppk

Be sure to give it a name, Save it, then Open session. (password is "vagrant")

The private key file does not seem to be needed

You are now at the point where you have a Ubuntu instance in a VM, and you are connected to it using Putty.  All the following commands are bash commands

### 3. Setup Docker in Ubuntu VM ###

Let's move on to Docker:

https://docs.docker.com/installation/ubuntulinux/#ubuntu-trusty-1404-lts-64-bit

    $ sudo apt-get update
    $ sudo apt-get install docker.io

We now test docker is working:

    $ sudo docker run -i -t ubuntu /bin/bash


    Unable to find image 'ubuntu' locally
    Pulling repository ubuntu
    9bd07e480c5b: Download complete
    511136ea3c5a: Download complete
    01bf15a18638: Download complete
    30541f8f3062: Download complete
    e1cdf371fbde: Download complete
    root@e5869c5004cf:/#

At this point you now have a vm running Ubuntu, which runs a docker instance running a
version of bash.  You may ```exit``` to get back to your Ubuntu command line.

We will add the ```vagrant``` user to the ```docker``` permission group:

    $ sudo usermod -a -G docker vagrant

You will need to reconnect so these permissions take hold.  Then  test to ensure you have permissions:

    $ docker ps
    CONTAINER ID        IMAGE               COMMAND             CREATED             STATUS              PORTS               NAMES

### 4. Setup Python in Ubuntu VM ###

Python is already installed on the vm, so we only need to install the Python tools.  First we download the package manager called Pip:

    wget https://bootstrap.pypa.io/get-pip.py

    Resolving bootstrap.pypa.io (bootstrap.pypa.io)... 23.235.46.175
    Connecting to bootstrap.pypa.io (bootstrap.pypa.io)|23.235.46.175|:443... connected.
    HTTP request sent, awaiting response... 200 OK
    Length: 1340903 (1.3M) [application/octet-stream]
    Saving to: âget-pip.pyâ

    100%[======================================>] 1,340,903   2.19MB/s   in 0.6s

    2014-12-16 22:23:41 (2.19 MB/s) - âget-pip.pyâ saved [1340903/1340903]

Execute that file with Python to install:

    $ sudo python get-pip.py
    Downloading/unpacking pip
      Downloading pip-1.5.6-py2.py3-none-any.whl (1.0MB): 1.0MB downloaded
    Downloading/unpacking setuptools
      Downloading setuptools-8.0.4-py2.py3-none-any.whl (550kB): 550kB downloaded
    Installing collected packages: pip, setuptools
    Successfully installed pip setuptools
    Cleaning up...

With Pip installed, the other packes are much easier.  We install the Python virtual environment manager and the Fig:  (responses not included)

    $ sudo pip install virtualenv
    $ sudo pip install fig

Grab the code from Github, (which also includes the docker files):

    $ git clone https://github.com/jmaher/alert_manager.git

We will use ```virtualenv``` to create a Python virtual environment, and activate it:

    $ virtualenv alert_manager
    $ cd alert_manager
    $ source bin/activate
    (alert_manager)vagrant@vagrant-ubuntu-trusty-64:~/alert_manager$

You have sucess when you see your prompt has changed.

### 5. Start Docker Instance ###

Docker is a Linux-only virtual environment manager. The required config files are in the repo, so all that remains is to ```make``` the Docker virtual environment:

<pre>
    $ cd dockerfiles
    $ make all
</pre>

A lot happens, and I have excluded those logs.  Hopefully it "just works".  Finally, Fig is used to bring up the instance, database and all:

<pre>
   $ fig up
    Recreating dockerfiles_database_1...
    Recreating dockerfiles_alertmanager_1...
    Attaching to dockerfiles_database_1, dockerfiles_alertmanager_1
    database_1     | /usr/lib/python2.7/dist-packages/supervisor/options.py:295: UserWarning: Supervisord is running as root and it is searching for its configurati                                                                   on file in default locations (including its current working directory); you prob                                                                   ably want to specify a "-c" argument specifying an absolute path to a configuration file for improved security.
    database_1     |   'Supervisord is running as root and it is searching '
    database_1     | 2014-12-17 20:11:16,833 CRIT Supervisor running as root (no user in config file)
    database_1     | 2014-12-17 20:11:16,833 WARN Included extra file "/etc/supervisor/conf.d/supervisord.conf" during parsing
    database_1     | 2014-12-17 20:11:16,882 INFO RPC interface 'supervisor' initialized
    database_1     | 2014-12-17 20:11:16,883 CRIT Server 'unix_http_server' running without any HTTP authentication checking
    database_1     | 2014-12-17 20:11:16,883 INFO supervisord started with pid 1
    database_1     | 2014-12-17 20:11:17,885 INFO spawned: 'mysql' with pid 8
    alertmanager_1 | INFO:werkzeug: * Running on http://0.0.0.0:8159/
    alertmanager_1 | INFO:werkzeug: * Restarting with reloader
    database_1     | 2014-12-17 20:11:19,412 INFO success: mysql entered RUNNING state, process has stayed up for > than 1 seconds (startsecs)
</pre>

We can test for success by opening your browser to [http://127.0.0.1:8080/alerts.html](http://127.0.0.1:8080/alerts.html)

