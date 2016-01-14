;-- START GCODE --
;Sliced for Type A Machines Series 1
;Sliced at: Mon 12-10-2015 10:09:49
;Basic settings: Layer height: 0.2 Walls: 0.8 Fill: 12
;Print Speed: 55 Support: 0
;Retraction Speed: 55 Retraction Distance: 1
;Print time: 0 minutes
;Filament used: 0.0m 0.0g
;Filament cost: None
G21        ;metric values
G90        ;absolute positioning
G28     ;move to endstops
G29		;allows for auto-levelling

;Layer count: 1
;LAYER:0
M107
;-- END GCODE --
M104 S0     ;extruder heater off
M140 S0     ;heated bed heater off (if you have it)
G91         ;relative positioning
G1 E-1 F300   ;retract the filament a bit before lifting the nozzle, to release some of the pressure
G1 Z+0.5 E-5 X-20 Y-20 F7200 ;move Z up a bit and retract filament even more
G28 X0 Y0     ;move X/Y to min endstops, so the head is out of the way
M84           ;steppers off
G90           ;absolute positioning

