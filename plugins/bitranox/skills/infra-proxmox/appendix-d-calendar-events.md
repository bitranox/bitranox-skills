# Calendar Events

*[Main Index](SKILL.md)*


## D.1 Schedule Format


Proxmox VE has a very flexible scheduling configuration. It is based on the systemd time calendar event
format.1 Calendar events may be used to refer to one or more points in time in a single expression.
Such a calendar event uses the following format:

[WEEKDAY] [[YEARS-]MONTHS-DAYS] [HOURS:MINUTES[:SECONDS]]
This format allows you to configure a set of days on which the job should run. You can also set one or
more start times. It tells the replication scheduler the moments in time when a job should start. With this
information we, can create a job which runs every workday at 10 PM: ’mon,tue,wed,thu,fri 22’
which could be abbreviated to: ’mon..fri 22’, most reasonable schedules can be written quite intuitive
this way.

> **Note:**
> Hours are formatted in 24-hour format.


To allow a convenient and shorter configuration, one or more repeat times per guest can be set. They
indicate that replications are done on the start-time(s) itself and the start-time(s) plus all multiples of the
repetition value. If you want to start replication at 8 AM and repeat it every 15 minutes until 9 AM you would
use: ’8:00/15’
Here you see that if no hour separation (:), is used the value gets interpreted as minute. If such a separation
is used, the value on the left denotes the hour(s), and the value on the right denotes the minute(s). Further,
you can use * to match all possible values.
To get additional ideas look at more Examples below.


## D.2 Detailed Specification


1 see man

7 systemd.time for more information


weekdays
Days are specified with an abbreviated English version: sun, mon, tue, wed, thu, fri
and sat. You may use multiple days as a comma-separated list. A range of days can also be set
by specifying the start and end day separated by “..”, for example mon..fri. These formats can be
mixed. If omitted ’*’ is assumed.
time-format
A time format consists of hours and minutes interval lists. Hours and minutes are separated by ’:’.
Both hour and minute can be list and ranges of values, using the same format as days. First are hours,
then minutes. Hours can be omitted if not needed. In this case ’*’ is assumed for the value of hours.
The valid range for values is 0-23 for hours and 0-59 for minutes.

> **Note:**
> You can use systemd-analyze calendar to see whether a given calendar event specification is
> valid and when it would be triggered next. By passing the --iterations=<N> flag you can also let it
> output the next <N> times the calendar event would trigger (you need to replace <N> with a valid integer).


### D.2.1 Examples:


There are some special values that have a specific meaning:

Table D.1: Special Values
Value

Syntax

minutely
hourly
daily
weekly
monthly
yearly or annually
quarterly
semiannually or semi-annually

*-*-* *:*:00
*-*-* *:00:00
*-*-* 00:00:00
mon *-*-* 00:00:00
*-*-01 00:00:00
*-01-01 00:00:00
*-01,04,07,10-01 00:00:00
*-01,07-01 00:00:00

Table D.2: Schedule Examples
Schedule String
mon,tue,wed,thu,fri
sat,sun
mon,wed,fri

Alternative
mon..fri
sat..sun
—

12:05
*/5

12:05
0/5

Meaning
Every working day at 0:00
Only on weekends at 0:00
Only on Monday, Wednesday
and Friday at 0:00
Every day at 12:05 PM
Every five minutes


Table D.2: (continued)
Schedule String
mon..wed 30/10

Alternative
mon,tue,wed 30/10

mon..fri 8..17,22:0/15

—

fri 12..13:5/20

fri 12,13:5/20

12,14,16,18,20,22:5

12/2:5

*
*-05
Sat *-1..7 15:00

*/1
—
—

2015-10-21

—

Meaning
Monday, Tuesday, Wednesday
30, 40 and 50 minutes after
every full hour
Every working day every 15
minutes between 8 AM and 6
PM and between 10 PM and 11
PM
Friday at 12:05, 12:25, 12:45,
13:05, 13:25 and 13:45
Every day starting at 12:05 until
22:05, every 2 hours
Every minute (minimum interval)
On the 5th day of every Month
First Saturday each Month at
15:00
21st October 2015 at 00:00
