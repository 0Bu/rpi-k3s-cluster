# Raspberry Pi OS configuration

### ssh
`ssh pi:raspberry@<IP>`

### Set default editor
```
sudo update-alternatives --config editor
sudo update-alternatives --set editor /usr/bin/vim.tiny
```

### Create a new user
`sudo adduser oleg`

### Sudoers
```
sudo adduser oleg sudo
sudo sh -c 'echo "oleg ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers.d/000_oleg-nopasswd'
```
### Delete ubuntu user
`sudo userdel -r pi`

### Disable welcome message
`sudo sh -c 'echo "" > /etc/motd'`

### Change hostname
```
hostnamectl
sudo hostnamectl set-hostname pi4
```

### Disable LED
Edit /boot/config.txt
```
[pi4]
dtparam=pwr_led_trigger=default-on
dtparam=pwr_led_activelow=off
dtparam=act_led_trigger=none
dtparam=act_led_activelow=off
dtparam=eth_led0=4
dtparam=eth_led1=4
```

### NTP Server
```
sudo apt update
sudo apt install ntp
echo "restrict 192.168.1.0 mask 255.255.255.0 nomodify notrap" >> /etc/ntp.conf
sudo /etc/init.d/ntp restart
```
