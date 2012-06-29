#!/usr/bin/python

import roslib
roslib.load_manifest('cob_generic_states_experimental')
import rospy
import smach
import smach_ros
from simple_script_server import *  # import script
sss = simple_script_server()

import tf
from std_msgs.msg import *
from sensor_msgs.msg import *
from geometry_msgs.msg import *
from cob_object_detection_msgs.msg import *
import tf_conversions.posemath as pm
import copy

def integrate_pose(pseudo_frame_as_pose, target_pose):
    return pm.toMsg(pm.fromMatrix( numpy.dot(pm.toMatrix(pm.fromMsg(pseudo_frame_as_pose)), pm.toMatrix(pm.fromMsg(target_pose))) ))

class PressButton(smach.State):
    def __init__(self):
        smach.State.__init__(self, 
            outcomes=['pressed','not_pressed','failed'],
            input_keys=['button'])
        self.listener = tf.TransformListener()
        rospy.Subscriber("/sdh_controller/one_pad_contact", Bool, self.touch_cb)
        rospy.Subscriber("/arm_controller/wrench", WrenchStamped, self.wrench_cb)
        self.arm_stop_request = False
        self.wrench_touch_treshold = 0.5
    
    def touch_cb(self,msg):
        if msg.data:
            self.arm_stop_request = True
    
    def wrench_cb(self,msg):
        if msg.wrench.force.z >= self.wrench_touch_treshold:
            self.arm_stop_request = True
         
    def execute(self, userdata):
        sss.say(["I am pressing a button now."])
        #print userdata.button
        
        #button_pose_bl = self.listener.transformPose("/base_link", userdata.button.pose)
        #[r,p,y] = tf.transformations.euler_from_quaternion([userdata.button.pose.pose.orientation.x,userdata.button.pose.pose.orientation.y,userdata.button.pose.pose.orientation.z,userdata.button.pose.pose.orientation.w])
        
        # move in front of button (initial rotation to orient finger to button)
        pose_offset = Pose()
        pose_offset.position.y = -0.1
        [new_x, new_y, new_z, new_w] = tf.transformations.quaternion_from_euler(-1.5708, 0.0, 0.0) # rpy 
        pose_offset.orientation.x = new_x
        pose_offset.orientation.y = new_y
        pose_offset.orientation.z = new_z
        pose_offset.orientation.w = new_w
        tmp_pose = copy.deepcopy(userdata.button.pose)
        tmp_pose.pose = integrate_pose(tmp_pose.pose, pose_offset)
        # pre_button_js
        pre_button_js, error_code = sss.calculate_ik(tmp_pose)
        if(error_code.val != error_code.SUCCESS):
            if error_code.val != error_code.NO_IK_SOLUTION:
                sss.set_light('red')
            rospy.logerr("Ik pre_button Failed")
            return 'not_pressed'

        # move towards button (relative movement in button_frame)
        pose_offset.position.y = 0.1
        tmp_pose = copy.deepcopy(userdata.button.pose)
        tmp_pose.pose = integrate_pose(tmp_pose.pose, pose_offset)
        # button_js
        button_js, error_code = sss.calculate_ik(tmp_pose)        
        if(error_code.val != error_code.SUCCESS):
            if error_code.val != error_code.NO_IK_SOLUTION:
                sss.set_light('red')
            rospy.logerr("Ik button Failed")
            return 'not_pressed'

        # move away from button (relative movement in button_frame)
        pose_offset.position.y = -0.1
        tmp_pose = copy.deepcopy(userdata.button.pose)
        tmp_pose.pose = integrate_pose(tmp_pose.pose, pose_offset)
        # post_button_js
        post_button_js, error_code = sss.calculate_ik(tmp_pose)        
        if(error_code.val != error_code.SUCCESS):
            if error_code.val != error_code.NO_IK_SOLUTION:
                sss.set_light('red')
            rospy.logerr("Ik button Failed")
            return 'not_pressed'

        sss.move_planned("arm", [list(pre_button_js.position)])
        handle_arm = sss.move("arm", [list(button_js.position)])
        
        self.arm_stop_request = False
        r = rospy.Rate(10)
        while not rospy.is_shutdown():
            if handle_arm.get_state() == 3:
                rospy.loginfo("arm reached button pose without touching the button")
                return 'not_pressed'
                break
            elif handle_arm.get_state() == 4:
                rospy.loginfo("arm movement was aborted")
                return 'not_pressed'
                break
            elif handle_arm.get_state() == 9:
                rospy.loginfo("arm movement is lost")
                break
            elif self.arm_stop_request:
                rospy.loginfo("arm stop requested")
                handle_arm.stop()
                break
            r.sleep()
        
        sss.move("arm", [list(post_button_js.position)])
        sss.move_planned("folded")
        return 'pressed'



















class SM(smach.StateMachine):
    def __init__(self):
        smach.StateMachine.__init__(self,outcomes=['ended'])
        with self:
            smach.StateMachine.add('STATE',PressButton(),
                    transitions={'pressed':'ended',
                                'not_pressed':'ended',
                                'failed':'ended'})

if __name__=='__main__':
    rospy.init_node('PressButton')
    sm = SM()
    sm.userdata.button = Detection()
    sm.userdata.button.pose.header.stamp = rospy.Time.now()
    sm.userdata.button.pose.header.frame_id = "/base_link"

	#simulation parameters
    sm.userdata.button.pose.pose.position.x = -0.55
    sm.userdata.button.pose.pose.position.y = 0.2
    sm.userdata.button.pose.pose.position.z = 1.1
    [new_x, new_y, new_z, new_w] = tf.transformations.quaternion_from_euler(2.44, -1.535, -1.552) # rpy 
	
	#real robot
    #sm.userdata.button.pose.pose.position.x = -0.5
    #sm.userdata.button.pose.pose.position.y = -0.1
    #sm.userdata.button.pose.pose.position.z = 1.0
    #[new_x, new_y, new_z, new_w] = tf.transformations.quaternion_from_euler(0.0, 0.0, 3.14) # rpy 

    sm.userdata.button.pose.pose.orientation.x = new_x
    sm.userdata.button.pose.pose.orientation.y = new_y
    sm.userdata.button.pose.pose.orientation.z = new_z
    sm.userdata.button.pose.pose.orientation.w = new_w

    sis = smach_ros.IntrospectionServer('SM', sm, 'SM')
    sis.start()
    outcome = sm.execute()
    rospy.spin()
    sis.stop()
