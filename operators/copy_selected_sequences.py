import bpy
from operator import attrgetter


class CopySelectedSequences(bpy.types.Operator):
    """
    Copies the selected sequences without frame offset.
    """

    bl_idname = "power_sequencer.copy_selected_sequences"
    bl_label = "Copy Selected Sequences"

    def execute(self, context):
        selection = context.selected_sequences
        cursor_start_frame = context.scene.frame_current
        sequencer = bpy.ops.sequencer

        # Deactivate audio playback
        scene = context.scene
        initial_audio_setting = scene.use_audio_scrub
        scene.use_audio_scrub = False

        first_sequence = min(selection, key=attrgetter('frame_final_start'))
        context.scene.frame_current = first_sequence.frame_final_start
        sequencer.copy()
        context.scene.frame_current = cursor_start_frame

        scene.use_audio_scrub = initial_audio_setting

        plural_string = 's' if len(selection) != 1 else ''
        report_message = 'Copied {!s} sequence{!s} to the clipboard.'.format(
            str(len(selection)), plural_string)
        self.report({'INFO'}, report_message)

        return {"FINISHED"}