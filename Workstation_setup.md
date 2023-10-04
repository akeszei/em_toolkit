# Notes on setting up EM processing workstation  

These notes are written as of Spring 2023, and are subject to changes in detail as newer versions of software are released. Never-the-less, the steps outlined here can serve as a useful guide for setting up a workstation in a stepwise manner. 

## Install Linux using a bootable USB 
A bootable USB can be created easily using [balenaEtcher](https://balenaetcher.org/) to flash a thumb drive with a linux distribution. These notes are written using [Linux Mint 21.1 "Vera" Cinnamon edition](https://www.linuxmint.com/edition.php?id=302). 

Plug in the USB and, if necessary, point the BIOS to boot from the thumb drive to run an instance of the OS from which you can easily install it onto your internal drive. Consider naming the computer something memorable/informative and making the first user `administrator`. 

## Update base install 
After installation, update base software:
```
$ sudo apt update -y && sudo apt upgrade -y
```

## Adjust `GRUB` settings
`GRUB` (GRand Unified Bootloader) is the principal software implemented for booting most linux distributions from BIOS. Hence, it is useful to expose its menu in case we wish to adjust the boot configuration at any time. We can do this by adjusting its config file and pushing the edits into `GRUB`.  

1. Edit config file via:
```
    $ sudo nano /etc/default/grub 
```
      ... change GRUB_TIMEOUT_STYLE=menu 
      ... change GRUB_TIMEOUT=8

2. Push settings to `GRUB` via:
```
    $ sudo update-grub 
```

## Mount disks permanently on `fstab`
Internal drives can be mounted permanently easily using the `disks` program. 

Common external drives that will be added/removed over time can be given fixed mount points so they automount on plugin/restart (avoiding need for `sudo` access) by adding their entry to the `fstab` file:
0. Prepare a mount point and make it accessible to all users. 
1. Plug in disk and find its UUID via. You may need to format it and mount it to get the UUID:
```
$ sudo blkid
Find its dev code via:
$ lsblk
or $ sudo fdisk -l
```
2. Add entry into `/etc/fstab` file, for example:
```sh
  ## Mount internal 2Tb SSD 
  UUID=c135a8dc-b2c1-418f-j114-255d94d8b401 /scratch ext4 defaults 0 2  
  ## Mount data_1 4Tb drive for all users  
  UUID=6146392E568902AB /media/usb/data_1  ntfs  user,gid=remote,umask=0002,rw,exec,X-mount.mkdir 0 2
```
3. If mounted automatically, unmount drive. Then test drive it mounts correctly via the `fstab` file to its target folder via:
```sh
  $ sudo mount -a 
```
You can repeat this procedure for any external drive. 

## Set up remote user account & add accounts to `users`
Prepare a `remote` user account, from which external users can login and run common software but have reduced permissions to important files & folders in the system. This will be the account with `ssh` access.

While editing accounts, it is useful to add both `administrator` and `remote` to a common group (e.g. `users`) to simplify permission structures later. 


## Install CUDA drivers & toolkit 
There are multiple ways to install CUDA drivers. This method follows the runfile method outlined by [nVidia docs](https://docs.nvidia.com/cuda/cuda-installation-guide-linux/index.html#runfile-overview), which installs the toolkit in a controlled location on disk for easier compiling of programs that need it. Below are steps that were taken for CUDA version 11.6.

### Download runfile 
CUDA 11.6 was targeted for install due to issues with higher versions that were not interrogated further. The runfile can be downloaded from [nVidia archives](https://developer.nvidia.com/cuda-11-6-0-download-archive). 

For Linux 21.1 select: `Linux` > `x86_64` > `Ubuntu` > `20.04` > `runfile (local)`

Use the given string (below) to download the driver, but do not run it until following the subsequent steps.
```
wget https://developer.download.nvidia.com/compute/cuda/11.6.0/local_installers/cuda_11.6.0_510.39.01_linux.run
```

### Pre-install preparation 
Double check the linux headers are installed:
```
    $ sudo apt-get install linux-headers-$(uname -r)
```
Then, prepare a blacklist file for native nouveau driver:

1. If not present, create a file at: `/usr/lib/modprobe.d/blacklist-nouveau.conf`
2. Edit its contents (use `$ sudo nano`) to contain: 
```
           blacklist nouveau 
           options nouveau modeset=0
```
3. Regenerate the kernel via:
```
    $ sudo update-initramfs -u 
```

### Reboot in full user text mode and prepare for install
Linux systems can be run in different modes with varying featuers/accessibility. To install the graphics drivers we need to be in text mode (runlevel 3) and ensure no other graphic drivers are active. 
1. Reboot, pausing on GRUB splash screen (use up/down arrow keys to pause timer). Then hit `e` on keyboard to edit boot options
2. To the line calling `linux ... quiet splash` add `3` at end to designate runlevel 3 (full user text mode). Continue with boot using these edited parameters with `Ctrl + X` 
3. Confirm nouveau is disabled by getting no return for:
```
    $ lsmod | grep nouveau 
```
4. Conform all X graphics are disabled by running:
```
    $ sudo service lightdm stop 
```

### Execute runfile 
Execute the runfile (you may need to make it executable):
```
    $ sudo chmod +x cuda_11...run
    $ sudo sh cuda_11.... .run
```
It may take time to unpack the installer, wait until it opens to accept the conditions and wait for it to finish. It can be useful to copy the output text of the installer for later reference. Reboot when ready. 

On reboot you should now get a graphical display. Use a terminal to confirm the drivers are installed and all GPUs are detected with `nvidia-smi`. If defaults were used you should also find the CUDA toolkit installed at `/usr/local/cuda-11.6` with a symlink of that folder next to it at `/usr/local/cuda`. 

### Add toolkit to `$PATH`
The final step is to add the toolkit binaries and compilers onto `$PATH` so it can be found by other programs. This is easily done by editing the user `~/.bashrc` file to include a check:
```
## Add CUDA toolkit to PATH
if [ -d /usr/local/cuda ]; then
    export LD_LIBRARY_PATH=/usr/local/cuda/lib64
    export PATH=$PATH:/usr/local/cuda/bin 
fi
```
If done correctly, then a fresh terminal window should show a return for:
```
    $ nvcc -V
```

## Install usual programs from aptitude
Add/remove packages as desired. This is a list of the usual suspects I use:

```
$ sudo apt install gedit git cmake fonts-inconsolata fonts-roboto ttf-mscorefonts-installer okular evince imagemagick gnuplot xorg openssh-server build-essential mpi-default-bin mpi-default-dev libfftw3-dev libtiff-dev python3-pip python3-setuptools libx11-dev tk8.6-dev python-tk csh tmux python3-tk python3-pil.imagetk yakuake tree gimp openconnect network-manager-openconnect
```

## Set up base python environment 
As of the time of writing these notes, aptitude installed python as `python3`. For simplicity, make this version the base version for the 'native' user environment by creating a symlink to this one at `/usr/bin` via:
```
    $ sudo ln -s /usr/bin/python3 /usr/bin/python 
```
Check that `pip` is also set up for this python version by checking its callback with:
```sh
    $ pip -V ## look for (python 3.x) in callback 
```
### Install common python modules to root account 
Using the root account to install a module makes it available for all users, preventing the need to install it in multiple locations: 
```
    $ sudo pip install matplotlib mrcfile numpy scipy opencv-python tifffile 
```

## Set up RSA keys & (if possible) SSH handshake the servers
If all programs are working properly, it is worth establishing a direct RSA handshake between all common servers so work can be transferred between them easily. 

### Set up user RSA key 
Each user will need its own key and must run through these steps independently. Generate a key via:
```sh
    $ ssh-keygen -t rsa -b 4096 -C "kasparov-remote"
```
When prompted use defaults and, for ease, to not add a passphrase (just hit enter). 

### If necessary, set the server to allow password attempts: 
It is good practice to lock a server so it does not allow password attempts. This way only known clients are accepted. However, for new clients, you need to temporarily allow password attempts so an initial handshake can be performed. This is done by editing the `sshd_config` file:
```sh 
    $ sudo nano /etc/ssh/sshd_config
      ## comment out: PasswordAuthentication no 
    $ service sshd restart ## restart service after saving
```

### Use password to add RSA key to server
The remote user can then use the username & password of the server to send its RSA key via:
```sh
    $ ssh-copy-id user@server-address
```
After this you can then lock the server to avoid password attempts if desired. 


## Optionally, customize user experience
For familiarity I like to install my own icon set and themes. This is easily done by copying the icon and theme sets into their respective folders from which they can then me 'installed' using the systems themes menu:
1. Icons can be installed at: `/usr/share/icons/`
```
    $ sudo cp -r AK_icon_theme /usr/share/icons/
```
2. Themes can be installed at: `/usr/share/themes/`
```sh
    $ sudo cp -r HighContrast_AK /usr/share/themes/ ## does not work Mint 21.1!
```
I like to change the clock format to include the date and time in AM/PM notation. Right click the clock and customize its display using this string:
```
    %Y/%m/%d | %l:%M%p
```

## Set up EM software & environment
Keeping together all programs related to processing in one place is helpful as the number and versions expands. It is also helpful for having a direct place to go for altering the base envrionment using an internal resource file. 

### Set up main parent folder
In this example, we make a folder at root `/` named `programs` and set its permissions so the administrator can work in it and the remote user can read & execute from it:
```sh
  $ sudo mkdir /programs 
  $ sudo chmod -R 750 /programs  
  $ sudo chown -R administrator /programs
  $ sudo chgrp -R users /programs 
```
If accessible, you can `scp` programs from another set up server to populate this one. 

### Set up resource file 
The resource file `bins.rc` can be copied from a set up server and adjusted as necessary to add programs onto the `$PATH` and set up useful variables/scripts. The location should be something like:
```sh
  /programs/bins.rc
``` 
Adjust this file as necessary to call out installed programs, for example it might look like:
```sh
## Add desired programs onto $PATH
export PATH=$PATH:\
/programs/relion/build/bin:\
/programs/chimera/bin:\
/programs/akeszei/bin:\
...
/programs/ctffind4/bin:\
/programs/coot/bin:\

## source phenix install via its bash script
source /programs/phenix/phenix-1.20.1-4487/phenix_env.sh

## export relion environment variables to change default paths to working bins
export RELION_MOTIONCOR2_EXECUTABLE=motioncor2
export RELION_CTFFIND_EXECUTABLE=ctffind 
export RELION_GCTF_EXECUTABLE=gctf 
export RELION_RESMAP_EXECUTABLE=resmap 
export RELION_PDFVIEWER_EXECUTABLE=okular

## Helpful script for calling command options.
if [ -f /programs/bash_howto ]; then
    . /programs/bash_howto
fi

## Helpful script for getting microscope parameters
if [ -f /programs/eminfo ]; then
    alias eminfo="/usr/bin/env bash /programs/eminfo"
fi
```

### Add resource file to user 
Source the main resource file in `/programs/` from the users' main `~/.bashrc` file via:
```sh
## Add binaries from /programs/bins.rc into $PATH
if [ -f /programs/bins.rc ]; then
    . /programs/bins.rc
fi
```
On terminal reload, programs added to `$PATH` by `bins.rc` will now be available. 


## Download & install usual programs from web 
To get the latest version of programs, or for programs not on aptitude, follow the online instructions to install these programs: 

### Inkscape
Follow the [ppa method](https://inkscape.org/release/inkscape-1.2.2/gnulinux/ubuntu/ppa/dl/) to install from the commandline. 

### VSCode
Just download the [.deb installer](https://code.visualstudio.com/download) and run it. 

### Chimera & ChimeraX
Notes to follow 

### Pyem
Notes to follow

### CrYOLO
Notes to follow

### Miniconda 
Get the [Linux 64-bit installer](https://docs.conda.io/en/latest/miniconda.html). Run the installer:
```sh
    $ bash ./Miniconda3-latest-Linux-x86_64.sh
```
When installer is complete, set it to initialize Miniconda3 before closing it. Then reopen a new terminal and set it not to auto-mount on startup via:
```sh
$ conda config --set auto_activate_base false
```
You will need to run this command on each account you wish to prevent auto-activation.


## (Optional) Setting up ZFS raid scratch space 
Notes are taken directly from [ubuntu docs](https://ubuntu.com/tutorials/setup-zfs-storage-pool#1-overview).

```sh
  ## Install zfs
  $ sudo apt install zfsutils-linux
  ## Use disks to delete the devices you want to raid
  ## Then make a fresh partition using 'Other' and 'No filesystem'
  ## Find the correct devices we want to pool via:
  $ sudo fdisk -l 
  $ lsblk
  ## In our case we want /dev/sda and /dev/sdb 
  ## Prepare a striped RAID-0 style pool via:
  $ sudo zpool create scratch /dev/sda /dev/sdb
  ## This will create a folder at root: /scratch, you can check the status via:
  $ zpool status 
  ## You will likely need to adjust the permissions status of this folder via:
  $ sudo chmod -R 775 /scratch
  $ sudo chgrp -R users /scratch
  $ sudo chown -R administrator /scratch 
```

## Install `relion` 
Follow instructions at its [git page](https://github.com/3dem/relion) to compile the program. 
```sh
  $ sudo apt install cmake git build-essential mpi-default-bin mpi-default-dev libfftw3-dev libtiff-dev libpng-dev ghostscript libxft-dev
  $ git clone https://github.com/3dem/relion.git
  ## I suggest making this a subfolder in case you need other versions
  $ mv relion relion_v4.0 
  $ mkdir relion 
  $ mv relion_v4.0 relion
  $ cd relion/relion_v4.0
  $ git checkout master # or ver4.0
  $ mkdir build
  $ cd build
  $ cmake ..
  $ make
```
There can be some issues building with newer `gcc`, `g++` compilers, e.g.:
```
...
CMake Error at relion_gpu_util_generated_cuda_projector_plan.cu.o.Release.cmake:280 (message): 
  Error generating file
...
``` 
In our case we succeeded by installing older versions and swapping the symlink at `/usr/bin` for the older version:
```sh
  $ sudo apt install gcc-10 g++-10
  ## Update the softlinks to point to them, i.e.
  ## /usr/bin/gcc -> /usr/bin/gcc-10
  ## /usr/bin/g++ -> /usr/bin/g++-10
```

## Install `cryoSPARC` 
There are excellent notes for installing at their [web page](https://guide.cryosparc.com/setup-configuration-and-management/how-to-download-install-and-configure). The key steps are outlined below.  

### Setup passwordless `ssh` 
```
$ ssh-keygen -t rsa -N "" -f $HOME/.ssh/id_rsa
$ ssh-copy-id cryosparc_user@localhost
```
Test you can login without a password prompt via:
```
$ ssh cryosparc_user@localhost 
```

### Request a license from: https://cryosparc.com/download 

### Prepare a directory to install the program into (use root user and change permissions):
Continuing the example above using a root `/programs` folder:
```sh
$ cd /programs
$ mkdir cryosparc
$ sudo chown -R cryosparc_user cryosparc
$ sudo chgrp -R cryosparc_user cryosparc
$ mkdir /scratch/cryosparc_cache
$ chmod 774 /scratch/cryosparc_cache/
```
### Download the tarballs:
```
  $ export LICENSE_ID="<license_id>"
  $ curl -L https://get.cryosparc.com/download/master-latest/$LICENSE_ID -o cryosparc_master.tar.gz
  $ curl -L https://get.cryosparc.com/download/worker-latest/$LICENSE_ID -o cryosparc_worker.tar.gz
```
Extract the archives
```
$ tar -xf cryosparc_master.tar.gz cryosparc_master
$ tar -xf cryosparc_worker.tar.gz cryosparc_worker
```

### Install the master 
```
$ cd cryosparc_master 
$ ./install.sh --standalone --license $LICENSE_ID --worker_path /programs/cryosparc/cryosparc_worker --cudapath /usr/local/cuda --ssdpath /scratch/cryosparc_cache --initial_email user@domain.com --initial_username "user" --initial_firstname "user" --initial_lastname "user" --initial_password <pw>
```

### Install the worker node
```sh
$ cd cryosparc_worker
$ ./install.sh --license $LICENSE_ID --cudapath /usr/local/cuda --yes
```

### Connect the worker node to the master 
```
$ cd cryosparc_worker 
$ ./bin/cryosparcw connect --worker localhost --master localhost --port 39000 --ssdpath /scratch/cryosparc_cache --lane default --newlane
```

## Install `cryoDRGN`
These are old notes on installing `cryoDRGN`:

```sh
# Install Node.js dependencies 
$ sudo apt install jupyter-core
$ sudo apt install nodejs npm
# REF: https://zhonge.github.io/cryodrgn/pages/installation.html
# As cryosparc_user, prepare the environment
$ conda create --name cryodrgn python=3.9
$ 
$ conda activate cryodrgn
$ conda install pytorch torchvision torchaudio pytorch-cuda=11.7 -c pytorch -c nvidia
$ conda install pandas seaborn scikit-learn
$ conda install umap-learn jupyterlab ipywidgets cufflinks-py "nodejs>=15.12.0" -c conda-forge
$ pip install jupyterlab
$ jupyter labextension install @jupyter-widgets/jupyterlab-manager --no-build
$ jupyter labextension install jupyterlab-plotly --no-build
$ jupyter labextension install plotlywidget --no-build
$ jupyter lab build
# Prepare a folder in /programs and set its permissions to cryosparc_user
$ mkdir -p /programs/cryoDRGN
$ sudo chgrp -R users /programs/cryoDRGN
$ sudo chown -R cryosparc_user /programs/cryoDRGN
# Download the git project 
$ cd /programs/cryoDRGN
$ git clone https://github.com/zhonge/cryodrgn.git
$ cd cryodrgn
$ pip install . 
```


## Install `NAMD` and accompanying simulation software 

### Installing `NAMD`
NAMD can be installed easily by requesting the CUDA enabled binaries from their [website](https://www.ks.uiuc.edu/Development/Download/download.cgi?PackageName=NAMD) (at the time of writing it was the `Linux-x86_64-multicore-CUDA` version).

On unzipping the software can be used immediately. For system-wide installation put it into the `/programs/` folder and add the binaries to the `$PATH`

### Installing `CPPTRAJ`
Pull the latest version from their [github page](https://github.com/Amber-MD/cpptraj). 
```
git clone https://github.com/Amber-MD/cpptraj.git 
```
Install it via several steps in `/programs`:
```
cd cpptraj
export CUDA_HOME=/usr/local/cuda
./configure -cuda -openmp gnu --buildlibs
```
If it runs successfully, source the envrionment script and continue with the installation:

```sh
source cpptraj.sh
make -j 12 install
## add a symlink so the program is recognized by its usual name
cd /programs/cpptraj/bin/
ln -s cpptraj.OMP.cuda cpptraj
## return to the main directory and run the test 
cd /programs/cpptraj 
make check 
```
For permanent installation, add the binaries and envrionment to the startup resource file `bins.rc`, e.g.:
```sh
export PATH=$PATH:\
...
/programs/cpptraj/bin:\

## source cpptraj envrionment via its bash script 
source /programs/cpptraj/cpptraj.sh
```