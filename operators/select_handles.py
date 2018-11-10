import bpy

# select handles
class SelectHandles(bpy.types.Operator):
    bl_idname = "power_sequencer.select_handles"
    bl_label = "Select Handles"
    bl_description = ""
    bl_options = {"REGISTER", "UNDO"}
    
    right=bpy.props.BoolProperty()

    @classmethod
    def poll(cls, context):
        return bpy.context.area.type=='SEQUENCE_EDITOR' and bpy.context.scene.sequence_editor is not None

    def execute(self, context):
        if self.right==True:
            bpy.ops.sequencer.strip_jump(next=True, center=False)
        else:
            bpy.ops.sequencer.strip_jump(next=False, center=False)
        FuncSelectHandles(self.right)
        return {"FINISHED"}
    
# select handles menu
class SelectHandlesMenu(bpy.types.Operator):
    bl_idname = "power_sequencer.select_handles_menu"
    bl_label = "Select Handles"
    bl_description = ""
    bl_options = {"REGISTER", "UNDO"}
    
    right=bpy.props.BoolProperty(name="Right")

    @classmethod
    def poll(cls, context):
        return bpy.context.area.type=='SEQUENCE_EDITOR' and bpy.context.scene.sequence_editor is not None
    
    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self, width=300, height=100)
    
    def check(self, context):
        return True
    
    def draw(self, context):
        layout = self.layout
        layout.prop(self, 'right')

    def execute(self, context):
        if self.right==True:
            bpy.ops.sequencer.strip_jump(next=True, center=False)
        else:
            bpy.ops.sequencer.strip_jump(next=False, center=False)
        FuncSelectHandles(self.right)
        return {"FINISHED"}
    
# select handles function
def FuncSelectHandles(right):
    scn=bpy.context.scene
    cf=scn.frame_current
    r_select=[]
    l_select=[]
    channel=[]
    trimlist=[]
    active=0
    for s in scn.sequence_editor.sequences_all:
        s.select=False
        s.select_left_handle=False
        s.select_right_handle=False
        if s.frame_final_start==cf:
            l_select.append(s)
        if s.frame_final_end==cf:
            r_select.append(s)
    for s in r_select:
        s.select=s.select_right_handle=True
    for s in l_select:
        s.select=s.select_left_handle=True
    
    return {"FINISHED"}
