# snippet

```snippet``` allows you to create, view and use snippets on the command-line.

## Example

```
# To view a snippet:
$ snippet -t archive/extract_tar -v
tar -xvf <archive>

# To get the prefilled snippet:
$ snippet -t archive/extract_tar '/path/to/foo.tar'
tar -xvf /path/to/foo.tar

# To add a new snippet:
$ snippet -e archive/extract_tgz -f 'tar -xzvf <archive>'

# To interactively search snippets which include the term "extract":
$ snippet -t extract -v
```

## Setup

```
git clone https://github.com/bytebutcher/snippet
cd snippet
python3 -m venv venv
./venv/bin/python3 install -r requirements.txt
sudo ln -s $PWD/snippet /usr/bin/snippet
```

To enable bash-completion you might add following line to your .bashrc:
```bash
eval "$(register-python-argcomplete3 snippet)"
```

## Usage

1. [Overview](#Overview)
2. [Assigning data to placeholders](#Assigning-data-to-placeholders)
   1. [Using positional arguments](#Using-positional-arguments)
   2. [Using environment variables](#Using-environment-variables)
   3. [Using presets](#Using-presets)
3. [Using string formats](#Using-string-formats)
   1. [Using on-the-fly transformation](#Using-the---format-string-argument)
   2. [Using input from a pipe](#Using-input-from-a-pipe)
   3. [Using templates](#Using-templates)
   4. [Using defaults](#Using-defaults)
   5. [Using optionals](#Using-optionals)
   6. [Using codecs](#Using-codecs)
4. [Executing commands](#Executing-commands)
5. [See also](#See-also)

### Overview

The following overview shows various examples of how ```snippet``` can be used:
```
# Adding or editing a snippet (will open vim)
$ snippet -e example
hello, <arg1>!

# Using arguments
$ snippet -t example world
hello, world!

# Using on-the-fly transformation 
$ snippet -f "hello, <arg1>!" world
hello, world!

# Using presets
$ snippet -f "hello, <arg>! It's <datetime>!" world
hello, world! It's 20770413000000!

# Using files
$ cat <<EOF > input.txt
world
universe
EOF
$ snippet -f "hello, <arg>!" arg:input.txt
hello, world!
hello, universe!

# Using repeatables
$ snippet -f "hello, <arg...>" arg:input.txt
hello, world universe

# Using optionals
$ snippet -f "hello[, <arg>]"
hello
$ snippet -f "hello[, <arg>]" world
hello, world!

# Using defaults
$ snippet -f "hello, <arg=world>!"
hello, world!

# Using codecs
$ snippet -f "echo 'hello <arg1>! (<arg1:b64>)';" world
echo 'hello, world! (cmV2YW1w)';
```

### Assigning data to placeholders
To assign data to a placeholder you have several options:

#### Using positional arguments
The most straight forward way of assigning data to a placeholder is to use positional arguments:

```
$ snippet -f "echo 'hello <arg1>';" snippet
echo 'hello snippet';
```

To assign multiple values to a specific placeholder you need to explicitly declare the placeholder to which the
value should be assigned to:
```
$ snippet -f "echo 'hello <arg1>';" arg1=snippet world
echo 'hello snippet';
echo 'hello world';
```

#### Using input files

Values can be directly imported from a file:
```
$ cat <<EOF > input.txt
world
universe
EOF
$ snippet -f "echo 'hello <arg1>';" arg1:input.txt
echo 'hello world';
echo 'hello universe';
```

#### Using environment variables

```snippet``` evaluates environment variables and assigns data to any unset 
placeholder. To avoid running into conflict with other environment variables ```snippet``` only evaluates 
lower-case variable names:
```
$ export arg1=snippet
$ snippet -f "echo 'hello <arg1>';"
echo 'hello snippet';
```
To assign multiple values to a placeholder following syntax must be used:
```
$ export arg1="\('snippet' 'world'\)"
$ snippet -f "echo 'hello <arg1>';"
echo 'hello snippet';
echo 'hello world';
```

Note that positional arguments may override the evaluation of environment variables:
```
$ export arg1=snippet
$ snippet -f "echo 'hello <arg1>';" world
echo 'hello world';
```

#### Using presets

```snippet``` ships with a customizable set of preset placeholders which can be 
directly used in your format string 
(see ```.snippet/snippet_profile.py``` for more information). Preset placeholders may have constant  
but also dynamically generated values assigned to them:
```
$ snippet -f "echo '<datetime>';" 
echo '20200322034102';
```

### Using string formats

To use string formats you have several options:

#### Using the --format-string argument

If you read the previous section you already know the ```-f | --format-string``` argument:

```
$ snippet -f "echo 'hello snippet';"
echo 'hello snippet';
```

#### Using input from a pipe

Another option to set the string format is by using a pipe:
```
$ echo "echo 'hello snippet'" | snippet
echo 'hello snippet';
```

#### Using templates

```snippet``` allows you to import format strings from a file by using the ```-t | --template``` argument.

There are two ways of creating a template:

1.  Create a file with the ```.snippet``` extension:
```
$ echo -n "echo 'hello, <arg>!'" > example.snippet
$ snippet -t example.snippet world!
```

2. Create a template using the ```-e | --edit``` argument:
```
# The following command will open vim
$ snippet -e example world!
$ snippet -t example world!
```

If you have bash-completion enabled you can press ```<TAB>``` twice to autocomplete 
template names. 

In addition the ```-t | --template``` argument will open an interactive search prompt 
when the specified template name was not found.

To list all available templates you can use the ```-l | --list-templates```
parameter.

#### Using codecs

```snippet``` supports simple string transformation. A list of available codecs can be viewed by using the
```--list-codecs``` argument.

To transform a placeholder use the ```<PLACEHOLDER[:CODEC ...]>``` format:
```
$ snippet -f "<arg:b64>" "hello snippet"
aGVsbG8gcmV2YW1w
$ snippet -f "<arg> <arg:b64:b64>" "hello snippet"
hello snippet YUdWc2JHOGdjbVYyWVcxdw==
```

#### Using defaults

```snippet``` supports specifying default values for your placeholders:

```
$ snippet -f "<arg1> <arg2=default>" hello
hello default
```

#### Using optionals

```snippet``` supports specifying optional parts in the string format by surrounding them with 
square-brackets:
```
$ snippet -f "<arg1> [<arg2>]" hello snippet
hello snippet
$ snippet -f "<arg1> [<arg2>]" hello
hello
$ snippet -f "<arg> [my <arg2=snippet>]" hello
hello my snippet
$ snippet -f "<arg> [my <arg2=snippet>]" hello arg2=
hello
```

If you need square-brackets to be part of the string format you need to
escape them accordingly:

```
$ snippet -f "\[<arg>\]" hello
[hello]
```

### Executing commands

```snippet``` can be used to easily execute alternating commands in sequence:
```
$ snippet -f "echo 'hello <arg1>';" arg1=snippet world | bash
hello world
hello snippet
```

Using ```xargs``` the resulting commands can also be executed in parallel:
```
snippet -f "echo 'hello <arg1>';" arg1=snippet arg1=world | xargs --max-procs=4 -I CMD bash -c CMD
hello world
hello snippet
```

## See also

To make the most out of this tool you might also consider to look into the following projects:
* [leval](https://github.com/bytebutcher/leval) - the lesser eval
* [interactive](https://github.com/bytebutcher/interactive) - make arbitrary commands interactive
* [bgl](https://github.com/bytebutcher/bgl) - manage global bash environment variables

Here is a rather advanced example of how ```interactive```, ```leval``` and ```snippet``` play together:
```
# Make snippet interactive and evaluate output using leval before executing it
$ interactive -p "leval --print-stdout" snippet -f "[format]" [args]
```