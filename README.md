Autotest
============
Input a swagger spec, autotest all APIs in the spec and validate responses.
<br>
<br>

How to use
----------------
<br>

###1.Prerequisites　###
Python2.7
<br>
<br>

###2.Install Related Package ###
    $ pip intall codecs
    $ pip intall datetime
    $ pip intall jinja2
    $ pip intall json
    $ pip intall re
    $ pip intall six
    $ pip intall yaml 
    $ pip intall logging
    $ pip intall logging.handlers
    $ pip intall requests
    $ pip intall six
    $ pip intall time
    $ pip intall tablib
<br>
<br>

###3.Editor Parameter Configure File ###
  Autotest provides two ways to get parameters.
  <br>

  (1) For simple Web APIs, just call the method get_example_from_prop_spec(self, prop_spec, param_name) in param_generator.py, it will return simple parameter according to the type of param.
  <br>

  (2) For some complex Web APIs, we must send valid params to the server side so that we could get valid resonse. Editor param_generator.py before testing.
  <br>
  Uber Example:
  <br>
    def uber_example():
      return {
          'latitude': 38.76623,
          'longitude': 116.43213,
          'start_latitude': 38.76623,
          'start_longitude': 116.43213,
          'end_latitude': 39.917023,
          'end_longitude': 116.396813,
          'access_token': 'CjCEg6plCW4SH1X3bVHjQKFpNtBeAD9TTcSVMg2k'
      }
      <br>
      <br>
      
###4.Define Response ###
   <br>

   We define three responses in my_tester.py：youku, uber, instagram. <br>
    def validate_youku_definition(swagger_parser, valid_response, response)
    def validate_uber_definition(swagger_parser, valid_response, response)
    def validate_ins_definition(swagger_parser, valid_response, response)
    
   If you want to test your own Web APIs, define your response in my_tester.py before testing.
   
###5.Execute testing###
<br>

   Autotest is easy to use, just execute the method swagger_test() in my_tester.py.<br><br>
    def swagger_test(swagger_yaml_path=None, app_url=None, authorize_error=None,<br>
                  wait_between_test=False, use_example=True)<br>
swagger_yaml_path: Your swagger file path in local.<br>
app_url : If you have a running Web APIs, you can test it like app_url = 'https://apis-guru.github.io/api-models/instagram.com/1.0.0'<br>
authorize_error: user-defined error, tester will ignore those errors.<br>
wait_between_test: Just preventing to be identified as a attacker by the server side.<br>
use_example: use user-defined params or not.
    <br>
    <br>
    
    
  
  
  
  
  
  
  
  
  
  
  
  
  
