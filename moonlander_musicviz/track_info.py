import subprocess

class TrackInfo:
    """
    Fetches current track info from macOS Music.app via AppleScript.
    """
    
    def get_current_track(self):
        """
        Returns a string like "Artist - Track" or "No Music" if failed/paused.
        """
        script = '''
        if application "Music" is running then
            tell application "Music"
                if player state is playing then
                    return (get artist of current track) & " - " & (get name of current track)
                else
                    return "Paused"
                end if
            end tell
        else
            return "Music App Closed"
        end if
        '''
        
        try:
            # Run applescript
            result = subprocess.run(
                ['osascript', '-e', script], 
                capture_output=True, 
                text=True, 
                timeout=0.5
            )
            
            if result.returncode == 0:
                output = result.stdout.strip()
                # Handle cases where output might be empty
                return output if output else "Unknown Track"
            else:
                return "No Info"
                
        except Exception:
            return "Info Error"
