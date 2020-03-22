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
```bash
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

$ bob -c "echo '<arg1> - <arg2>'" -i input.csv 
```

In addition bob ships with a customizable set of default placeholders which can be directly used in your command (see ```.bob/profile.py``` for more information):
```
$ bob -c "echo '<date_time>'" 
```

You can also use the ```--environment``` argument to import the command format or placeholder data from your environment:
```
$ export COMMAND_FORMAT="echo '<arg1> - <arg2> - <date_time>'"
$ export arg1=bob
$ export arg2="\('the command builder' 'generating commands from data'\)"
$ bob -e
```

If you happen to type the same command over and over again there is just another feature. Template-files:
```
$ mkdir ~/.bob/templates
$ echo -n "echo '<arg1> - <arg2> - <date_time>'" > ~/.bob/templates/example
$ bob -t example -i input.csv
```

You can list all available templates using the ```-l | --list-templates``` parameter.
However, if you have bash-completion enabled you also can press <TAB> twice to autocomplete 
template names when using the ```-t | --template``` parameter. 

To enable bash-completion add following line to your .bashrc:
```bash
eval "$(register-python-argcomplete bob)"
```
Make sure that you link bob the executable accordingly:
```bash
ln -s /path/to/bob.py /usr/bin/bob
```

### Interactive Shell

If you feel that using bob via the standard command line is a bit too tedious you can always drop into the interactive shell:
```
$ bob --interactive
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