# revamp

```revamp``` is an advanced highly customizable template based string formatting tool which
has the ability to do complex variable substitutions and string transformation.

## Setup

```
git clone https://github.com/bytebutcher/revamp
cd revamp
python3 -m venv venv
./venv/bin/python3 install -r requirements.txt
sudo ln -s $PWD/revamp /usr/bin/revamp
```

To enable bash-completion you might add following line to your .bashrc:
```bash
eval "$(register-python-argcomplete revamp)"
```
Make sure to add the ```revamp``` directory to your ```PATH``` or link it accordingly:
```
ln -s /path/to/revamp.py /usr/bin/revamp
```

## Usage

1. [Overview](#Overview)
2. [Assigning data to placeholders](#Assigning-data-to-placeholders)
   1. [Using positional arguments](#Using-positional-arguments)
   2. [Using environment variables](#Using-environment-variables)
   3. [Importing from csv-files](#Importing-from-csv-files)
   4. [Using presets](#Using-presets)

3. [Using string formats](#Using-string-formats)
   1. [Using the --format-string argument](#Using-the---format-string-argument)
   2. [Using templates](#Using-templates)
4. [Transforming strings using codecs](#Transforming-strings-using-codecs)
5. [Executing commands](#Executing-commands)
6. [See also](#See-also)

### Overview

The following overview shows various examples of how ```revamp``` can be used:
```
# A rather simple string format example using revamp
$ revamp -f "hello <arg1>" revamp
hello revamp

# Assigning multiple values and making use of presets
$ revamp -f "ping -c 1 <rhost> > ping_<rhost>_<date_time>.log;" rhost=localhost github.com
ping -c 1 localhost > ping_localhost_20770413000000.log;
ping -c 1 github.com > ping_github.com_20770413000000.log;

# Using templates and reading arguments from a file
$ revamp -t net/scan/nmap-ping rhost:hosts.txt
nmap -vvv -sP localhost -oA nmap-ping_localhost_20770413000000
nmap -vvv -sP github.com -oA nmap-ping_github.com_20770413000000

# When no template is specified an interactive template search prompt will be displayed
$ revamp rhost:hosts.txt

# Transforming strings
$ revamp -f "echo 'hello <arg1> (<arg2>)';" -c arg2=arg1:b64 revamp
echo 'hello revamp (cmV2YW1w)';
```

### Assigning data to placeholders
To assign data to a placeholder you have several options:

#### Using positional arguments
The most straight forward way of assigning data to a placeholder is to use positional arguments:

```
$ revamp -f "echo 'hello <arg1>';" revamp
echo 'hello revamp';
```

To assign multiple values to a specific placeholder you need to explicitly declare the placeholder to which the
value should be assigned to:
```
$ revamp -f "echo 'hello <arg1>';" arg1=revamp world
echo 'hello revamp';
echo 'hello world';
```

In addition values can be directly imported from a file:
```
$ cat <<EOF > input.txt
revamp
world
EOF
$ revamp -f "echo 'hello <arg1>';" arg1:input.txt
echo 'hello world';
echo 'hello revamp';
```

#### Using environment variables

```revamp``` evaluates environment variables and assigns data to any unset 
placeholder. To avoid running into conflict with other environment variables ```revamp``` only evaluates 
lower-case variable names:
```
$ export arg1=revamp
$ revamp -f "echo 'hello <arg1>';"
echo 'hello revamp';
```
To assign multiple values to a placeholder following syntax must be used:
```
$ export arg1="\('revamp' 'world'\)"
$ revamp -f "echo 'hello <arg1>';"
echo 'hello revamp';
echo 'hello world';
```

Note that positional arguments may override the evaluation of environment variables:
```
$ export arg1=revamp
$ revamp -f "echo 'hello <arg1>';" world
echo 'hello world';
```
 
#### Importing from csv-files

Data can also be imported from a csv-file using the ```-i | --import``` argument.
Note, that values must be separated by a tab character
 (which can be changed in ```.revamp/revamp_profile.py```):

```
$ cat <<EOF > input.csv
arg1    arg2
hello   revamp
        world
EOF
$ revamp -f "echo '<arg1> <arg2>';" -i input.csv 
echo 'hello world';
echo 'hello revamp';
```

#### Using presets

```revamp``` ships with a customizable set of preset placeholders which can be 
directly used in your format string 
(see ```.revamp/revamp_profile.py``` for more information). Preset placeholders may have constant  
but also dynamically generated values assigned to them:
```
$ revamp -f "echo '<date_time>';" 
echo '20200322034102';
```

### Using string formats

To use string formats you have several options:

#### Using the --format-string argument

If you read the previous section you already know the ```-f | --format-string``` argument:

```
$ revamp -f "echo 'hello revamp';"
echo 'hello revamp';
```

#### Using input from a pipe

Another option to set the string format is by using a pipe:
```
$ echo "echo 'hello revamp'" | revamp
echo 'hello revamp';
```

#### Using templates

If you want to persist your format string you can add them to ```revamp```'s template directory
which can be easily accessed using the ```-t | --template``` argument:
```
$ mkdir -p ~/.revamp/templates
$ echo -n "echo '<arg1> <arg2> - <date_time>'" > ~/.revamp/templates/example
$ revamp -t example arg1=hello arg2=revamp
hello revamp - 20200322034102
```

If you have bash-completion enabled you can press ```<TAB>``` twice to autocomplete 
template names. 

If you want to review a specific template you can use the ```-tV | --template-view``` argument:
```
$ revamp -t example -tV
echo '<arg1> <arg2> - <date_time>'
```

To list all available templates you can use the ```-tL | --template-list```
parameter:

```
$ revamp -tL
net/enum/enum4linux-basic
net/scan/nmap-basic
net/scan/nmap-ping
net/scan/nmap-syn
net/scan/nmap-version
os/exec/bash-curl
os/exec/bash-wget
os/exec/cmd-webdav
os/exec/powershell-http
os/exec/powershell-webdav
os/exec/xargs-parallel
shell/listener/nc
shell/listener/ncat
shell/listener/netcat
shell/listener/socat
shell/reverse/linux/groovy
shell/reverse/linux/java
shell/reverse/linux/perl
shell/reverse/linux/php
shell/reverse/linux/python
shell/reverse/linux/ruby
shell/reverse/multi/powershell
shell/reverse/multi/python
shell/reverse/multi/socat
shell/reverse/windows/groovy
shell/reverse/windows/perl
shell/reverse/windows/ruby
shell/upgrade/pty
web/fuzz/gobuster-basic
web/fuzz/nikto-basic
web/fuzz/wfuzz-basic
web/fuzz/wfuzz-ext
```

### Transforming strings using codecs

```revamp``` supports simple string transformation. A list of available codecs can be viewed by using the
```--codec-list | -cL``` argument:

```
$ revamp -cL
b64
md5
safe_filename
sha1
sha256
sha512
url
url_plus
```

To transform a placeholder use the ```--codec | -c``` argument by specifying the placeholder to transform and the codec
to use:
```
$ revamp -f "<arg>" -c arg:b64 arg="hello revamp"
aGVsbG8gcmV2YW1w
```

To do a subsequent string transformation on the same placeholder just specify another codec:
```
$ revamp -f "<arg>" -c arg:b64:md5 arg="hello revamp"
fa06bfedcbfa6b6d0384baebc644b666
```

If you require the initial and the transformed value at the same time ```revamp``` allows to store the transformed value
in a new placeholder:
```
$ revamp -f "<arg> - <arg2>" -c arg2:arg:b64:md5 arg="hello revamp"
hello revamp - fa06bfedcbfa6b6d0384baebc644b666
```

### Executing commands

```revamp``` can be used to easily execute alternating commands in sequence:
```
$ revamp -f "echo 'hello <arg1>';" arg1=revamp world | bash
hello world
hello revamp
```

Using ```xargs``` the resulting commands can also be executed in parallel:
```
revamp -f "echo 'hello <arg1>';" arg1=revamp arg1=world | xargs --max-procs=4 -I CMD bash -c CMD
hello world
hello revamp
```

## See also

To make the most out of this tool you might also consider to look into the following projects:
* [leval](https://github.com/bytebutcher/leval) - the lesser eval
* [interactive](https://github.com/bytebutcher/interactive) - make arbitrary commands interactive
* [bgl](https://github.com/bytebutcher/bgl) - manage global bash environment variables

Here is a rather advanced example of how ```interactive```, ```leval``` and ```revamp``` play together:
```
# Make revamp interactive and evaluate output using leval before executing it
$ interactive -p "leval --print-stdout" revamp -f "[format]" [args]
```