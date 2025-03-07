# sh-sched-tracker

This project was initiated by a friend who works in the IT department for Southampton (Long Island, NY) shool system. That school system uses three different school schedules. My friend wnated be able to see what the active 'period' was, at any given time, at a glance. 

BASIC FUNCTIOALITY DESCRIPTION

A small main window appear on app launch. 
The window displat three message boxes whose labels are the names of the three school schedules (Regular, 2-Hour Delay, and Homeroom).
The app constantly compares the current time to informaiton in a schedule json file to provide 5 differetn messages:
 - 00:00 to start of any given schedule the message displayed is 'Before School'
 - Start of schdule to start of period 1 the message displayed is 'Period 1 sarts at {period 1 start time}'
 - from period start to period end the message displayed is 'Period {number}' or '{period name}' (ex. Extra Help, Homeroom)
 - In between perios the message displayed is 'Period {number} -> Period {number}"
 - From 14:30 to 23:59 the displayed message is 'After School'

This is useful for school employess that need to track students down and need to know where in the schedule at a quick glance they are at any given moment to locate the student in the building. 


VERSION INFO

4 versions were made along the path of getting him the solution he was happy with:

PyQt6 - This verison is the first complete deskotp app verison I coded. It works very well cross platform when compiled using pyinstaller. A Windows installer was created with InnoSetup 6 whihc worked fine on all my dev machines but not on my friends school PC so I created the other verisons to see what would work for him.

PyQt5 - This version is exactly the same as Qt6 version just using Qt5 becasue my friend had a problem install and running the Qt6 verison on his particular PC. I did this as an attempt to figure out the problem. All my own Windows dev machines handeled the stfware with no instalaltion and operational problems. This verison was never actually tested or used outside of my dev environment.

Tkinter - I wroet this version for the same reason as the Qt5 version. I was thinking that with Tkinter being so closely integrated with Python it woudl solve potential instaltion and operaiton problems. 

Web (HTML/JS/CSS) - I settled on this verison becasue I thought it woudl be the most cross platform. My friend really wnated a desktop and mobile version of the app. I have never done a true iOS or Android project so I opted for a front end onyl web app for a quick and easy solution. 


FEATURE DETAILS:

App Window Sizing
 - Fixed Windwow Size [Tk/Web]
 - Variable Window Size (3 fixed choices) [Qt5/Qt6]

App Window Position
 - saved between app launches [Qt5/Qt6/Tk]

Sys Tray Icon
 - Has tray icon [Qt5/Qt6/Tk]
 - Schedule info shown on tray icon tooltip [Qt5/Qt6/Tk]
 - Clicking icon minimizes/maximizes app windwow [Qt5/Qt6(Windows Only)]
 - Selectable icon image [Qt5/Qt6]

Color Settings
 - Window Background and Text [Qt5/Qt6/Tk]
 - Schedule Message Box Background, Labels and Text [All]
 - settings are saved [All]

Schedule Editing
 - in app editor [Qt5/Qt6/Tk]
 - password protected [Qt5/Qt6]

Test Mode
 - manual test mode [Qt5/Qt6/Tk]
 - automatic test mode [All]
 - password protected [All]
 
 *** Test mode use either a manually set time or loads time data in from a text file to be able to see what meesage will occur at those test times to validate proper schedule messaging.

Admininistration
 - default admin password is 'shs' [All]
 - admin reset password is 'chucksoft'
 - admin password can be changed [Qt5/Qt6]
 - admin password can be rest if forgotten [Qt5/Qt6]
 
