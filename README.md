# bob
bob the command builder - generating commands from data

## Usage

```
usage: bob [-h] [-c COMMAND_FORMAT_STRING]
           [-s PLACEHOLDER=VALUE | -s PLACEHOLDER:FILE] [-i FILE] [-t FILE]
           [-l] [-f STRING]

Bob - the command builder

optional arguments:
  -h, --help            show this help message and exit
  -c COMMAND_FORMAT_STRING, --command-string COMMAND_FORMAT_STRING
                        The format of the command. The placeholders are
                        identified by less than (<) and greater than (>)
                        signs.
  -s PLACEHOLDER=VALUE | -s PLACEHOLDER:FILE, --set PLACEHOLDER=VALUE | -s PLACEHOLDER:FILE
                        The value(s) used to replace the placeholder found in
                        the command format. Values can either be directly
                        specified or loaded from file.
  -i FILE, --import FILE
                        The value(s) used to replace the placeholder found in
                        the command format.
  -t FILE, --command-template FILE
                        The format of the command as specified by the
                        template.
  -l, --command-template-list
                        Lists all available command templates.
  -f STRING, --filter STRING
                        The filter to include/exclude results (e.g. -f
                        'PLACEHOLDER==xx.* and PLACEHOLDER!=.*yy').

Default placeholders:

  <date>               current date %Y%m%d
  <date_time>          current date and time %Y%m%d%H%M%S

Examples:

  bob -s target=localhost     -c "nmap -sS -p- <target> -oA nmap-syn-all_<target>_<date_time>"
  bob -s target:./targets.txt -c "nmap -sS -p- <target> -oA nmap-syn-all_<target>_<date_time>"
   
```
