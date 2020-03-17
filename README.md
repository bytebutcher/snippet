# bob
bob the command builder - generating commands from data

## Usage

We start with the simplest (and probably most boring) example of how to use bob:  
```
$ bob -c "echo '<arg1>'" -s arg1=bob 
```

The command above will return one simple line of output:
```bash
echo 'bob'
```

That's indeed not very impressive. Let's look at another example.:
```
$ bob -c "echo '<arg1> - <arg2>'" -s arg1=bob -s "arg2=the command builder" -s "arg2=generating commands from data" 
```

As you can see we specified multiple values for arg2. As a result bob will return the following lines:
```
echo 'bob - the command builder'
echo 'bob - generating commands from data'
```

Lets create some file named input.txt and look at yet another example:
```
$ cat <<EOF > input.txt
the command builder
generating commands from data
EOF
$ bob -c "echo '<arg1> - <arg2>'" -s arg1=bob -s arg2:./input.txt 
```

As you can see you do not need to specify each and every value using the ```-s | --set``` operator but can load them from a file instead.

Data can also be imported from a csv-file whereby values must be separated by a tab character (which can be changed in ```.bob/profile.py```):
```
$ cat input.csv
arg1    arg2
bob     the command builder
        generating commands from data

$ bob -c "echo '<arg1> - <arg2>'" -i targets.csv 
```

In addition bob ships with a customizable set of default placeholders which can be directly used in your command (see ```.bob/profile.py``` for more information):
```
$ bob -c "echo '<arg1> - <arg2> - <date_time>'" -i targets.csv
```

If you happen to type the same command over and over again there is just another feature. Template-files:
```
$ mkdir ~/.bob/templates
$ echo -n "echo '<arg1> - <arg2> - <date_time>'" > ~/.bob/templates/example
$ bob -t example -i targets.csv
```

You can list all available templates using the ```-l | --list-templates``` parameter.
However, if you have bash-completion enabled you also can press <TAB> twice to autocomplete 
template names when using the ```-t | --template``` parameter. 

To enable bash-completion add following line to your .bashrc:
```buildoutcfg
eval "$(register-python-argcomplete bob)"
```
Make sure that you link bob the executable accordingly:
```buildoutcfg
ln -s /path/to/bob.py /usr/bin/bob
```
