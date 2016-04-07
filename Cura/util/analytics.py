import time
from datetime import date
import urllib2
from Cura.util import profile
import platform
from Cura.util import version



def featureAnalytics(MS,BS,DU,DSV,featureName):
	# featureName = material_selector , direct_upload , batch_slice , design_space_visualization
	if profile.getPreference('submit_slice_information') != 'True':
		return
	
	date_MS = ''
	date_BS = ''
	date_DU = ''
	date_DSV = ''
	#print MS
	#print (MS is '1')
	if MS is '1':
		date_MS = str(date.fromtimestamp(time.time())) #2016-01-13
	elif BS is '1':
		date_BS = str(date.fromtimestamp(time.time())) #2016-01-13
	elif DU is '1':
		date_DU = str(date.fromtimestamp(time.time())) #2016-01-13
	elif DSV is '1':
		date_DSV = str(date.fromtimestamp(time.time())) #2016-01-13


	formID = '1yqfZA9nsgAyOTSH32u7Q8gTXTFRuu6fgxozeOkL9d94'
	requestURL = 'https://docs.google.com/forms/d/'+formID+'/formResponse?ifq&'

	formData = 'entry.1519716307='+date_MS+'&entry.289194511='+date_DU+'&entry.27522520='+date_BS+'&entry.525119059='+date_DSV+'&entry.1922183683='+featureName+'&entry.534228141='+MS+'&entry.1274829210='+BS+'&entry.1268483657='+DU+'&entry.59616272='+DSV
#	print formData
	URL = requestURL + formData
	resp = urllib2.urlopen(URL)
	print 'feature analytics uploaded' , resp

def analyticsOnSave(self):
	size_x = str(round(float(self._scene.objects()[0].getSize()[0]),2))
	size_y = str(round(float(self._scene.objects()[0].getSize()[1]),2))
	size_z = str(round(float(self._scene.objects()[0].getSize()[2]),2))
	#print_time = str(self._printTimeSeconds) #urstr(self._printTimeSeconds)
	m, s = divmod(self._printTimeSeconds, 60)
	h, m = divmod(m, 60)
	print_time = "%d:%02d:%02d" % (h, m, s)
	layer_height = str(profile.getProfileSettingFloat('layer_height'))
	infill_type = str(profile.getProfileSetting('infill_type'))
	sparse_infill_line_distance = 'None'
	if profile.getProfileSetting('infill_type') != 'None':
		sparse_infill_line_distance = str(profile.getProfileSettingFloat('fill_density'))
	wall_thickness = str(profile.getProfileSettingFloat('wall_thickness'))
	cura_profile_string = str(self._profileString)
	#try :
	url = 'https://docs.google.com/forms/d/1ZYnwO7qUprv9OxEROPqVxJYxiwoD-FDryECB8E1d9nI/formResponse?ifq&entry.521154058='+size_x+'&entry.671353976='+size_y+'&entry.13086712='+size_z+'&entry.1978610599='+print_time+'&entry.41743500='+layer_height+'&entry.1372370450='+infill_type+'&entry.1122747225='+sparse_infill_line_distance+'&entry.1165297693='+wall_thickness+'&entry.1389723193='+cura_profile_string
	resp = urllib2.urlopen(url)
	print 'SUBMITTED' , resp
	url = 'https://docs.google.com/forms/d/10oPd6RVwbucO7MkM3JYgxWO4lykjTeeAE0523b9XCjk/formResponse?ifq&entry.934083010='+platform.processor()+'&entry.273325052='+platform.machine()+'&entry.170849433='+platform.platform()+'&entry.1350805925='+version.getVersion()
	resp = urllib2.urlopen(url)
