# revamp

## Usage

We start with the simplest (and probably most boring) example of how to use revamp:  
```
$ revamp -c "echo '<arg1>'" -s arg1=revamp 
```

The command above will return one simple line of output:
```bash
echo 'revamp'
```

That's indeed not very impressive. Let's look at another example.:
```
$ revamp -c "echo '<arg1> - <arg2>'" -s arg1=revamp -s "arg2=the command builder" -s "arg2=generating commands from data" 
```

As you can see we specified multiple values for arg2. As a result revamp will return the following lines:
```bash
echo 'revamp - the command builder'
echo 'revamp - generating commands from data'
```

Lets create some file named input.txt and look at yet another example:
```
$ cat <<EOF > input.txt
the command builder
generating commands from data
EOF
$ revamp -c "echo '<arg1> - <arg2>'" -s arg1=revamp -s arg2:./input.txt 
```

As you can see you do not need to specify each and every value using the ```-s | --set``` operator but can load them from a file instead.

Data can also be imported from a csv-file using the ```-i | --import``` argument.
Note, that values must be separated by a tab character (which can be changed in ```.revamp/revamp_profile.py```):
```
$ cat input.csv
arg1    arg2
revamp     the command builder
        generating commands from data

$ revamp -c "echo '<arg1> - <arg2>'" -i input.csv 
echo 'revamp - the command builder'
echo 'revamp - generating commands from data'
```

You can also import the command format or placeholder data from your environment by using the ```-e | --environment``` argument:
```
$ export COMMAND_FORMAT="echo '<arg1> - <arg2>'"
$ export arg1=revamp
$ export arg2="\('the command builder' 'generating commands from data'\)"
$ revamp -e
echo 'revamp - the command builder'
echo 'revamp - generating commands from data'
```

In addition revamp ships with a customizable set of preset placeholders which can be directly used in your command (see ```.revamp/revamp_profile.py``` for more information):
```
$ revamp -c "echo '<date_time>'" 
echo '20200322034102'
```

If you want to persist your command format you can add them to revamp's template directory
which can be easily accessed using the ```-t | --template``` argument:
```
$ mkdir -p ~/.revamp/templates
$ echo -n "echo '<arg1> - <arg2> - <date_time>'" > ~/.revamp/templates/example
$ revamp -t example -i input.csv
```

You can list all available templates using the ```-l | --list-templates``` parameter.
However, if you have bash-completion enabled you can also press <TAB> twice to autocomplete 
template names when using the ```-t | --template``` parameter. 

To enable bash-completion add following line to your .bashrc:
```bash
eval "$(register-python-argcomplete revamp)"
```
Make sure that you link revamp the executable accordingly:
```bash
ln -s /path/to/revamp.py /usr/bin/revamp
```

### Interactive Shell

If you feel that using revamp via the standard command line is a bit too tedious you can always drop into the interactive shell:
```
$ revamp --interactive
Type '%help' for more information
In [1]: %help                                                                                                                                                                                                                                                     
%use command_format <string>
    set the command format e.g. %use command_format 'test <date_time>'.
%use template <string>
    set the command format via a template name e.g. %use template test.
%show command_format
    shows the current command format.
%show options
    shows the current list of potential placeholders and values.
%show templates [filter_string]
    shows the available list of templates. The list can be filtered by specifying a filter string.
%set <placeholder=value|placeholder:file>
    sets a potential placeholder and the associated values.
%unset <placeholder>
    unsets a potential placeholder.
%import <file> [delimiter]
    imports data from a given csv-file. The default delimiter is \t.
%build
    builds the commands.
%help
    show this help.
``` 