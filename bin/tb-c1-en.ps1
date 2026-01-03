    Start-Sleep -Milliseconds 250
    Clear-Host
    Start-Sleep -Milliseconds 250

# Type your clan as example $clanname1 = 'Lords of Dragons'
# see your configuration file config/config.cfg for $clanname!
    $clanname1 = 'Lords of Dragons'
    $clanname2 = 'Your 2nd clan'
    $clanname3 = 'Your 3rd clan'
    $clanname4 = 'Your 4th clan'

# -- Correct install-path, if needed --
    $main = "c:\chest-counter\"
# -------------------------------------
        
        # do not touch!
        $path         = $main + "bin\"
        $dpath        = $main + "data\"
        $working      = $main + "working-c1"
        $archive      = $main + "archive-c1"
        $players      = $main + "config\players-c1.csv"
        $players_c2   = $main + "config\players-c2.csv"
        $players_c3   = $main + "config\players-c3.csv"
        $players_c4   = $main + "config\players-c4.csv"
        Set-Location -Path $path

    Start-Sleep -Milliseconds 500
    write-host "========================================================" -foregroundcolor Cyan
    write-host "= Chest-Tracker by Lady Cara - Version 17-11-2025      =" -foregroundcolor yellow
    write-host "= [u] Check for Updates: Lords of Dragons Wiki         =" -foregroundcolor yellow
    write-host "========================================================" -foregroundcolor Cyan
    write-host "- [i]nfos  [y]t-Video  [p]wsh update  [v]ersion python -" -foregroundcolor green
    write-host "- Install the [4] Libraries than do [5] Calibration    -" -foregroundcolor green
    write-host "========================================================" -foregroundcolor Cyan
    write-host ""
    write-host ">>>>>>> Your Clan : $clanname1" -ForegroundColor white
    write-host ">>>>>>>>>>>>>>>>>>>>>>>>>>>>><<<<<<<<<<<<<<<<<<<<<<<<<<<" -foregroundcolor yellow
    write-host ">> Run TB PC-App and switch to the Language: ENGLISH  <<" -foregroundcolor yellow
    write-host ">>>>>>>>>>>>>>>>>>>>>>>>>>>>><<<<<<<<<<<<<<<<<<<<<<<<<<<" -foregroundcolor yellow
    write-host ">> [1] : Capture Chests (captured-datas)              <<" -foregroundcolor white
    write-host ">> [2] : Summary Score                                <<" -foregroundcolor white
    write-host ">> [3] : Summary Total Score (total-datas)            <<" -foregroundcolor white
    write-host ">> [4] : Install Libraries, also after python update  <<" -foregroundcolor white
    write-host ">> [C] : Show Calibration Example before do [5]       <<" -foregroundcolor white
    write-host ">> [5] : Calibration (Text & Open-Buton Coordinates)  <<" -foregroundcolor white
    write-host ">> [6] : Summary from a day                           <<" -ForegroundColor white
    write-host ">> [E] : Exclude retired player | Namechange 'rename' <<" -ForegroundColor white
    write-host ">> [R] : Restore retired player                       <<" -ForegroundColor white
    write-host ">> [S] : Sort in alphabetical order all playerlists   <<" -ForegroundColor white
    write-host ">> [x] : Exit                                         <<" -foregroundcolor white
    write-host ">>>>>>>>>>>>>>>>>>>>>>>>>>>>><<<<<<<<<<<<<<<<<<<<<<<<<<<" -foregroundcolor yellow
    write-host ">> [7] : Change to $clanname2" -ForegroundColor white
    write-host ">> [8] : Change to $clanname3" -ForegroundColor white
    write-host ">> [9] : Change to $clanname4" -ForegroundColor white
    write-host ">>>>>>>>>>>>>>>>>>>>>>>>>>>>><<<<<<<<<<<<<<<<<<<<<<<<<<<" -foregroundcolor yellow
    write-host ">> At '[1] Capture Chests' each time the new chests   <<" -foregroundcolor green
    write-host ">> will be added, until the capture-file is removed.  <<" -foregroundcolor green
    write-host ">> At the End of the week/month, if you have removed  <<" -foregroundcolor green 
    write-host ">> the data/capture-datas.txt, you can press [3] &    <<" -foregroundcolor green 
    write-host ">> you get Total-Scores from your total-data-file.    <<" -foregroundcolor green 
    write-host ">> Tip: Capture 24h. Example from 7 p.m. to 7 p.m.    <<" -foregroundcolor green
    write-host ">>>>>>>>>>>>>>>>>>>>>>>>>>>>><<<<<<<<<<<<<<<<<<<<<<<<<<<" -foregroundcolor yellow
    write-host "`n"
    
    $value = $null
    $value = Read-Host "Choose [1-9] [C-E-R-S] [i-y-p-u-v] or [x] "
   
    if ($value -eq 1)
        {Clear-Host
        write-host ""
        write-host ">>>>>>>>>>>>>>>>>>>>>>>>>>>>><<<<<<<<<<<<<<<<<<<<<<<<<<<" -foregroundcolor green
        write-host ">> ! CHECK ! Are you in the RIGHT CLAN to capture the <<" -foregroundcolor yellow
        write-host ">> Chests? All the values from the Gift-Screen get    <<" -foregroundcolor yellow
        write-host ">> added to your new or existing capture-file.        <<" -foregroundcolor yellow
        write-host ">>>>>>>>>>>>>>>>>>>>>>>>>>>>><<<<<<<<<<<<<<<<<<<<<<<<<<<" -foregroundcolor green
        write-host ">> Your Clan : $clanname1" -foregroundcolor white
        write-host ">> Chest Counter started!" -foregroundcolor white
        write-host "" -foregroundcolor yellow
        py .\tb.py --config '..\config\config-c1.cfg' --capture}

    elseif ($value -eq 2)
        {Clear-Host
        write-host ""
        write-host ">> Your Clan : $clanname1" -foregroundcolor white
        write-host ">>>>>>>>>>>>>>>>>>>>>>>>>>>>><<<<<<<<<<<<<<<<<<<<<<<<<<<" -foregroundcolor yellow
        write-host ">> Summary Score as example for a day from 7pm to 7pm <<" -foregroundcolor yellow
        write-host ">>>>>>>>>>>>>>>>>>>>>>>>>>>>><<<<<<<<<<<<<<<<<<<<<<<<<<<" -foregroundcolor yellow
        write-host ">> In your data-folder there are new created summary- <<" -foregroundcolor green
        write-host ">> files. If this is your final-summary for today,    <<" -foregroundcolor green
        write-host ">> than delete the capture-file to start a new one.   <<" -foregroundcolor green
        write-host ">>>>>>>>>>>>>>>>>>>>>>>>>>>>><<<<<<<<<<<<<<<<<<<<<<<<<<<" -foregroundcolor yellow
        write-host ">>> Summary Files in Process!                        <<<" -foregroundcolor yellow
        write-host ">>>>>>>>>>>>>>>>>>>>>>>>>>>>><<<<<<<<<<<<<<<<<<<<<<<<<<<" -foregroundcolor yellow
        write-host ""
        write-host ""
        write-host ""
        py .\tb.py --config '..\config\config-c1.cfg' --process --summary}
    
    elseif ($value -eq 3)
        {Clear-Host
        write-host ""
        write-host ">>> Your Clan : $clanname1" -foregroundcolor white
        write-host ">>>>>>>>>>>>>>>>>>>>>>>>>>>>><<<<<<<<<<<<<<<<<<<<<<<<<<<" -foregroundcolor yellow
        write-host ">>> Total Summary as example for a week or a month   <<<" -foregroundcolor yellow
        write-host ">>>>>>>>>>>>>>>>>>>>>>>>>>>>><<<<<<<<<<<<<<<<<<<<<<<<<<<" -foregroundcolor yellow
        write-host ">>> Important: If your captured-data.txt is present  <<<" -foregroundcolor green
        write-host ">>> it get renamed to backup-captured-datas.txt      <<<" -foregroundcolor green
        write-host ">>>>>>>>>>>>>>>>>>>>>>>>>>>>><<<<<<<<<<<<<<<<<<<<<<<<<<<" -foregroundcolor yellow
        write-host ">>> Start Total-Summary with [y] or Abort with [x]   <<<" -foregroundcolor yellow
        write-host ">>>>>>>>>>>>>>>>>>>>>>>>>>>>><<<<<<<<<<<<<<<<<<<<<<<<<<<" -foregroundcolor yellow
        write-host ""
        $totalscore = Read-Host "[y] or [x] "
        if ($totalscore -eq 'y')
            {
            # Check if original capture file is present, if yes, backup
            $dori = $dpath + "captured-datas-c1.txt"
            if (test-path -path $dori) {Rename-Item -Path $dori -NewName "backup-captured-datas-c1.txt"}
            # Total Summary erstellen
            $dpath = $dpath + "total-datas-c1.txt"
            Rename-Item -Path $dpath -NewName "captured-datas-c1.txt"
            py .\tb.py --config '..\config\config-c1.cfg' --process --summary
            }
            else {& ".\tb-c1-en.ps1"}
        } 
    
    elseif ($value -eq 4)
        {Clear-Host
        write-host "" -foregroundcolor Green
        write-host "------------------------------------" -foregroundcolor Green
        write-host "Libraries will be installed/updated!" -foregroundcolor Green
        write-host "------------------------------------" -foregroundcolor Green
        write-host "" -foregroundcolor Green
        Start-Sleep -Milliseconds 3000
        py -m pip install --upgrade pip
        py -m pip install clipboard
        py -m pip install pytesseract
        py -m pip install pyautogui
        py -m pip install imutils
        write-host ""
        write-host "-----------------------------------" -foregroundcolor Green
        write-host "Patience, long installation process" -foregroundcolor Green
        write-host "-----------------------------------" -foregroundcolor Green
        write-host "" -foregroundcolor white
        py -m pip install opencv-contrib-python
        write-host "`n"
        write-host "----------------------------------" -foregroundcolor Green
        write-host "Libs Installed/Updated/fixed/Done!" -foregroundcolor Green
        write-host "----------------------------------" -foregroundcolor Green
        Start-Sleep -Milliseconds 5000
        & ".\tb-c1-en.ps1"}

    elseif ($value -eq 5)
        {Clear-Host
        write-host "" -foregroundcolor yellow
        write-host "Chest Screen calibration started!" -foregroundcolor yellow
        write-host "" -foregroundcolor yellow
        py .\tb.py --config '..\config\config-c1.cfg' --calibrate}
    
    elseif ($value -eq 6)
        {Clear-Host
        write-host ""
        write-host ">>>>>>>>>>>>>>>>>>>>>>>>>>>>><<<<<<<<<<<<<<<<<<<<<<<<<<<" -foregroundcolor yellow
        write-host ">>> SUMMARY FROM A DAY ONLY, MUST BE IN ARCHIVE!     <<<" -foregroundcolor yellow
        write-host ">>>>>>>>>>>>>>>>>>>>>>>>>>>>><<<<<<<<<<<<<<<<<<<<<<<<<<<" -foregroundcolor yellow
        write-host ">>> The Day must be written as example : 2025-10-28  <<<" -foregroundcolor yellow
        write-host ">>>>>>>>>>>>>>>>>>>>>>>>>>>>><<<<<<<<<<<<<<<<<<<<<<<<<<<" -foregroundcolor yellow
        write-host ""
        $day = Read-Host "Year-Month-Day or x"
        if ($day -eq 'x'){& ".\tb-c1-en.ps1"}
        else {py .\tb.py --config '..\config\config-c1.cfg' --process --summary --start_date $day --end_date $day}
        }

    elseif ($value -eq 7)
        {& ".\tb-c2-en.ps1"}

    elseif ($value -eq 8)
        {& ".\tb-c3-en.ps1"}

    elseif ($value -eq 9)
        {& ".\tb-c4-en.ps1"}

    elseif ($value -eq 'E' -or $value -eq 'e' -or $value -eq 'n' -or $value -eq 'N')
        {
            # Exclude retired/lost Player with xxRETIREDxx
            Start-Sleep -Milliseconds 250
            Clear-Host
            Start-Sleep -Milliseconds 250
            $find_a =""
            $find_b =""
            $rename_a =""
            $rename_b =""
            $content =""
            $newcontent =""
            $track = 0
            write-host ""
            write-host ">> Your Clan : $clanname1" -foregroundcolor white
            write-host ">>>>>>>>>>>>>>>>>>>>>>>>>>>>><<<<<<<<<<<<<<<<<<<<<<<<<<<" -foregroundcolor yellow
            write-host ">> Module : Exclude or Rename Player                  <<" -foregroundcolor yellow
            write-host ">>>>>>>>>>>>>>>>>>>>>>>>>>>>><<<<<<<<<<<<<<<<<<<<<<<<<<<" -foregroundcolor yellow
            write-host ">> [1] : Exclude Playername, which is retired         <<" -foregroundcolor white
            write-host ">> [2] : Rename Player because of 'Namechange'        <<" -foregroundcolor white
            write-host ">> [M] : Back to Menu                                 <<" -foregroundcolor white
            write-host ">> [x] : Exit                                         <<" -foregroundcolor white
            write-host ">>>>>>>>>>>>>>>>>>>>>>>>>>>>><<<<<<<<<<<<<<<<<<<<<<<<<<<" -foregroundcolor yellow
            write-host ""
            write-host ""

            $choice = $null
            $choice = Read-Host "Chose [1-2] [M] or [x] "

            if ($choice -eq 'x' -or $choice -eq 'X')
            {write-host ""
            write-host "-- EXIT --"
            write-host ""
            Start-Sleep -Milliseconds 2000
            [System.Environment]::Exit(0)
            break}

            if ($choice -eq 'M' -or $input -eq 'm')
            {write-host ""
            Start-Sleep -Milliseconds 2000
            & ".\tb-c1-en.ps1"}            

            if ($choice -eq '1')
            {   $track = 1
                write-host ""
                write-host ">>>>>>>>>>>>>>>>>>>>>>>>>>>>><<<<<<<<<<<<<<<<<<<<<<<<<<<" -foregroundcolor yellow
                write-host ">> Module : Find and Rename lost players              <<" -foregroundcolor yellow
                write-host ">>>>>>>>>>>>>>>>>>>>>>>>>>>>><<<<<<<<<<<<<<<<<<<<<<<<<<<" -foregroundcolor yellow
                write-host ">> [1] : Type the Playername, which is retired        <<" -foregroundcolor white
                write-host ">>>>>>>>>>>>>>>>>>>>>>>>>>>>><<<<<<<<<<<<<<<<<<<<<<<<<<<" -foregroundcolor yellow
                write-host ">> Type the exact Playername, which it is in your     <<" -foregroundcolor green
                write-host ">> player.csv and which are retired. The playername   <<" -foregroundcolor green
                write-host ">> get renamed to xxRETIREDxx_Playername in the       <<" -foregroundcolor green
                write-host ">> player.csv and into your working-database.         <<" -foregroundcolor green
                write-host ">>>>>>>>>>>>>>>>>>>>>>>>>>>>><<<<<<<<<<<<<<<<<<<<<<<<<<<" -foregroundcolor yellow
                write-host ""
                write-host ""
                $input = Read-Host "Find [1] ?"
                $find = ": " + $input
                $find_a = "Source"
                $find_b = $input + ","
                $rename = ": xxRETIREDxx_" + $input
                $rename_b = "xxRETIREDxx_" + $find_b
                clear-host
                Start-Sleep -Milliseconds 100
                write-host ""
                write-host ""
                write-host ">>>>>>>>>>>>>>>>>>>>>>>>>>>>><<<<<<<<<<<<<<<<<<<<<<<<<<<" -foregroundcolor green
                write-host "> Find Player $input and mark as xxRETIREDxx            " -foregroundcolor yellow
                write-host "> If you have a large database, the process may take    " -foregroundcolor yellow
                write-host "> some time. The process can run in the background,     " -foregroundcolor yellow
                write-host "> that allowing you to perform other tasks in parallel. " -foregroundcolor yellow
                write-host ">>>>>>>>>>>>>>>>>>>>>>>>>>>>><<<<<<<<<<<<<<<<<<<<<<<<<<<" -foregroundcolor green
                write-host ""
                Start-Sleep -Milliseconds 16000
            }
            if ($choice -eq '2')
            {   $track = 2
                write-host ""
                write-host ">>>>>>>>>>>>>>>>>>>>>>>>>>>>><<<<<<<<<<<<<<<<<<<<<<<<<<<" -foregroundcolor yellow
                write-host ">> Module : Find and Rename players                   <<" -foregroundcolor yellow
                write-host ">>>>>>>>>>>>>>>>>>>>>>>>>>>>><<<<<<<<<<<<<<<<<<<<<<<<<<<" -foregroundcolor yellow
                write-host ">> [1] : Type the Playername, before renamed          <<" -foregroundcolor white
                write-host ">> [2] : Type the actual/renamed Playername           <<" -foregroundcolor white
                write-host ">>>>>>>>>>>>>>>>>>>>>>>>>>>>><<<<<<<<<<<<<<<<<<<<<<<<<<<" -foregroundcolor yellow
                write-host ">> Type the exact Playername, which it is in your     <<" -foregroundcolor green
                write-host ">> player.csv and than his new name. The playername   <<" -foregroundcolor green
                write-host ">> get renamed to the new Playername in the           <<" -foregroundcolor green
                write-host ">> player.csv and into your working-database.         <<" -foregroundcolor green
                write-host ">>>>>>>>>>>>>>>>>>>>>>>>>>>>><<<<<<<<<<<<<<<<<<<<<<<<<<<" -foregroundcolor yellow
                write-host ""
                write-host ""
                $input  = Read-Host "The old Playername [1] ?"
                $actual = Read-Host "The new Playername [2] ?"
                $find = ": " + $input
                $find_a = "Source"
                $find_b = $input + ","
                $rename = ": " + $actual
                $rename_b = $actual + ","
                clear-host
                Start-Sleep -Milliseconds 100
                write-host ""
                write-host ""
                write-host ">>>>>>>>>>>>>>>>>>>>>>>>>>>>><<<<<<<<<<<<<<<<<<<<<<<<<<<" -foregroundcolor green
                write-host "> Find Player $input and rename to $actual              " -foregroundcolor yellow
                write-host "> If you have a large database, the process may take    " -foregroundcolor yellow
                write-host "> some time. The process can run in the background,     " -foregroundcolor yellow
                write-host "> that allowing you to perform other tasks in parallel. " -foregroundcolor yellow
                write-host ">>>>>>>>>>>>>>>>>>>>>>>>>>>>><<<<<<<<<<<<<<<<<<<<<<<<<<<" -foregroundcolor green
                write-host ""
                Start-Sleep -Milliseconds 16000
            }
            
            if ($choice -eq '1' -or $choice -eq '2')
            {
                # --------------------------
                # Exclude + Rename : Working
                # --------------------------
                $a = 0
                $z = 0
            
                # Alle .txt Dateien im Ordner Working abrufen
                Get-ChildItem -Path $working -Filter "*.txt" | ForEach-Object {
                $a += 1
                $file = $_
                $content = Get-Content -Path $file.FullName

                write-host ">>>>> Process Working File : $a" -foregroundcolor yellow

                # Save Inhalt in eine temp Variable
                $newcontent = @()

                    # Alle Zeilen durchsuchen
                    for ($i = 0; $i -lt $content.Length; $i++) {
                        $currentrow = $content[$i]

                        # Überprüfen, ob die aktuelle Zeile das zu suchende Wort enthält
                        if ($currentrow -like "*$find") {
                        # Überprüfen, ob es eine nächste Zeile gibt
                        if ($i + 1 -lt $content.Length) {
                        $nextrow = $content[$i + 1]

                        # Überprüfen, ob die nächste Zeile das Source-Wort enthält
                        if ($nextrow -like "$find_a*") {
                            # Zeile mit dem Eingabewort ersetzen
                            $newcontent += $currentrow -replace $find, $rename
                            $z += 1

                        } else {
                            # Keine Treffer
                            $newcontent += $currentrow
                        }
                    
                        } else {
                        # Keine nächste Zeile vorhanden
                        $newcontent += $currentrow
                        }
                    
                        } else {
                        # Zeile, die das Wort nicht enthält, unverändert lassen
                        $newcontent += $currentrow
                        }
                    }

                # Den neuen Inhalt zurück in die Datei schreiben
                $newcontent | Set-Content -Path $file.FullName
                }

                # -------------------------------
                # Exclude + Rename : Archive
                # -------------------------------
                $a2 = 0
                $z2 = 0
            
                # Alle .txt Dateien im Ordner Archive abrufen
                Get-ChildItem -Path $archive -Filter "*.archive" | ForEach-Object {
                $a2 += 1
                $file = $_
                $content = Get-Content -Path $file.FullName

                write-host ">>>>> Process Archive File : $a2" -foregroundcolor yellow

                # Save Inhalt in eine temp Variable
                $newcontent = @()

                    # Alle Zeilen durchsuchen
                    for ($i = 0; $i -lt $content.Length; $i++) {
                        $currentrow = $content[$i]

                        # Überprüfen, ob die aktuelle Zeile das zu suchende Wort enthält
                        if ($currentrow -like "*$find") {
                        # Überprüfen, ob es eine nächste Zeile gibt
                        if ($i + 1 -lt $content.Length) {
                        $nextrow = $content[$i + 1]

                        # Überprüfen, ob die nächste Zeile das Source-Wort enthält
                        if ($nextrow -like "$find_a*") {
                            # Zeile mit dem Eingabewort ersetzen
                            $newcontent += $currentrow -replace $find, $rename
                            $z2 += 1

                        } else {
                            # Keine Treffer
                            $newcontent += $currentrow
                        }
                    
                        } else {
                        # Keine nächste Zeile vorhanden
                        $newcontent += $currentrow
                        }
                    
                        } else {
                        # Zeile, die das Wort nicht enthält, unverändert lassen
                        $newcontent += $currentrow
                        }
                    }

                # Den neuen Inhalt zurück in die Datei schreiben
                $newcontent | Set-Content -Path $file.FullName
                }

                # -------------------------------
                # Exclude + Rename : Data
                # -------------------------------
                $a1 = 0
                $z1 = 0
            
                # Alle .txt Dateien im Ordner Data abrufen
                Get-ChildItem -Path $dpath -Filter "*c1.txt" | ForEach-Object {
                $a1 += 1
                $file = $_
                $content = Get-Content -Path $file.FullName

                write-host ">>>>> Process Data File : $a1" -foregroundcolor yellow

                # Save Inhalt in eine temp Variable
                $newcontent = @()

                    # Alle Zeilen durchsuchen
                    for ($i = 0; $i -lt $content.Length; $i++) {
                        $currentrow = $content[$i]

                        # Überprüfen, ob die aktuelle Zeile das zu suchende Wort enthält
                        if ($currentrow -like "*$find") {
                        # Überprüfen, ob es eine nächste Zeile gibt
                        if ($i + 1 -lt $content.Length) {
                        $nextrow = $content[$i + 1]

                        # Überprüfen, ob die nächste Zeile das Source-Wort enthält
                        if ($nextrow -like "$find_a*") {
                            # Zeile mit dem Eingabewort ersetzen
                            $newcontent += $currentrow -replace $find, $rename
                            $z1 += 1

                        } else {
                            # Keine Treffer
                            $newcontent += $currentrow
                        }
                    
                        } else {
                        # Keine nächste Zeile vorhanden
                        $newcontent += $currentrow
                        }
                    
                        } else {
                        # Zeile, die das Wort nicht enthält, unverändert lassen
                        $newcontent += $currentrow
                        }
                    }

                # Den neuen Inhalt zurück in die Datei schreiben
                $newcontent | Set-Content -Path $file.FullName
                }

                clear-host
                Start-Sleep -Milliseconds 100
                
                if ($track -eq 1)
                {
                write-host ""
                write-host ""
                write-host ">>>>>>>>>>>>>>>>>>>>>>>>>>>>><<<<<<<<<<<<<<<<<<<<<<<<<<<" -foregroundcolor green
                write-host "> Player $input get marked as xxRETIREDxx               " -foregroundcolor yellow
                write-host ">>>>>>>>>>>>>>>>>>>>>>>>>>>>><<<<<<<<<<<<<<<<<<<<<<<<<<<" -foregroundcolor green
                write-host ""
                write-host ">>>>> Process Working Files  : $a" -foregroundcolor yellow
                write-host ">>>>> Process Archive Files  : $a2" -foregroundcolor yellow
                write-host ">>>>> Process Data Files     : $a1" -foregroundcolor yellow
                }
                if ($track -eq 2)
                {
                write-host ""
                write-host ""
                write-host ">>>>>>>>>>>>>>>>>>>>>>>>>>>>><<<<<<<<<<<<<<<<<<<<<<<<<<<" -foregroundcolor green
                write-host "> Player $input get renamed as $actual                  " -foregroundcolor yellow
                write-host ">>>>>>>>>>>>>>>>>>>>>>>>>>>>><<<<<<<<<<<<<<<<<<<<<<<<<<<" -foregroundcolor green
                write-host ""
                write-host ">>>>> Process Working Files  : $a" -foregroundcolor yellow
                write-host ">>>>> Process Archive Files  : $a2" -foregroundcolor yellow
                write-host ">>>>> Process Data Files     : $a1" -foregroundcolor yellow
                }

                if ($z -gt 0){write-host ">>>>> Renamed Player @Working : $z" -foregroundcolor yellow}
                if ($z2 -gt 0){write-host ">>>>> Renamed Player @Archive : $z2" -foregroundcolor yellow}
                if ($z1 -gt 0){write-host ">>>>> Renamed Player @Data    : $z1" -foregroundcolor yellow}
                if ($z -lt 1){write-host ">>>>> Player '$input' not found @Working" -foregroundcolor yellow}
                if ($z2 -lt 1){write-host ">>>>> Player '$input' not found @Archive" -foregroundcolor yellow}
                if ($z1 -lt 1){write-host ">>>>> Player '$input' not found @Data" -foregroundcolor yellow}

                # Prüfen, ob das exakte Wort in der Spielerconfig vorhanden ist
                # \b steht für eine Wortgrenze, um nur das Wort zu finden
                $playerexists = Select-String -Path $players -Pattern "\b$find_b\b" -Quiet

                if ($playerexists) {
                    $content = Get-Content -Path $players -Raw
                    $newcontent = $content -creplace "\b$find_b\b", $rename_b
                    Set-Content -Path $players -Value $newcontent
                        # Read, sort, delete empty rows and write Player.csv back
                        $content = Get-Content -Path $players
                        $contentfilter = $content | Where-Object {$_.Trim() -ne ""}
                        $sort = $contentfilter | Sort-Object
                        $sort | Set-Content -Path $players
                        #$content = Get-Content -Path $players
                        #$content | Sort-Object | Set-Content -Path $players
                        
                        write-host ""
                        write-host ">>>>> Open your players.csv and check the aliases for your " -foregroundcolor white
                        write-host ">>>>> player, if no more needed, remove or modify aliasses " -foregroundcolor white
                        write-host ">>>>>                                                      " -foregroundcolor white
                        write-host ">>>>> The player.csv should look like:                     " -foregroundcolor white
                        write-host ">>>>> name,lowercase name,alias1,alias2......              " -foregroundcolor white

                } else {
                    Write-Host ""
                    Write-Host ">>>>> Oooops, something went wrong:                     " -foregroundcolor white
                    Write-Host ">>>>> The Player '$input'                               " -foregroundcolor white
                    Write-Host ">>>>> was not found into the players.csv, it can happen " -foregroundcolor white
                    Write-Host ">>>>> if there is no lowercase name or alliasses =>     " -foregroundcolor white
                    write-host ">>>>> Please check your players.csv manually            " -foregroundcolor white
                    write-host ">>>>>                                                   " -foregroundcolor white
                    write-host ">>>>> The player.csv should look like:                  " -foregroundcolor white
                    write-host ">>>>> name,lowercase name,alias1,alias2..               " -foregroundcolor white
                }

                write-host ""
                write-host ">>>>>>>>>>>>>>>>>>>>>>>>>>>>><<<<<<<<<<<<<<<<<<<<<<<<<<<" -foregroundcolor yellow
                write-host ">>> PROCESS COMPLETED - CHECK your players.csv       <<<" -foregroundcolor yellow
                write-host ">>>>>>>>>>>>>>>>>>>>>>>>>>>>><<<<<<<<<<<<<<<<<<<<<<<<<<<" -foregroundcolor yellow
                write-host ""
                Start-Sleep -Milliseconds 3000
                write-host ""
                write-host ""
                write-host ">>>>>>>>>>>>>>>>>>>>>>>><<<<<<<<<<<<<<<<<<<<<" -foregroundcolor yellow
                write-host ">>> E[x]it or type another Key for [M]enu <<<" -foregroundcolor yellow
                write-host ">>>>>>>>>>>>>>>>>>>>>>>><<<<<<<<<<<<<<<<<<<<<" -foregroundcolor yellow
                write-host ""
                    # Play with ANY-KEY :D
                    $input = Read-Host " [X] or [ANY-KEY] ? "
                    if ($input -eq 'x' -or $input -eq 'X')
                        {write-host ""
                        write-host "-- EXIT --"
                        write-host ""
                        Start-Sleep -Milliseconds 2000
                        [System.Environment]::Exit(0)
                        break}
                    else
                        {write-host ""
                        write-host "-- ANY-KEY --"
                        write-host ""
                        Start-Sleep -Milliseconds 3000
                        & ".\tb-c1-en.ps1"}
            }
        }

    elseif ($value -eq 'x')
        {write-host ""
        write-host "-- EXIT --"
        write-host ""
        Start-Sleep -Milliseconds 2000
        [System.Environment]::Exit(0)
        break}
    
    elseif ($value -eq 'R' -or $value -eq 'r')
        {
            # Restore retired/lost Player, remove xxRETIREDxx from the playername
            Start-Sleep -Milliseconds 250
            Clear-Host
            Start-Sleep -Milliseconds 250
            $find_a =""
            $find_b =""
            $rename_a =""
            $rename_b =""
            $content =""
            $newcontent =""
            write-host ""
            write-host ">>>>>>>>>>>>>>>>>>>>>>>>>>>>><<<<<<<<<<<<<<<<<<<<<<<<<<<" -foregroundcolor yellow
            write-host ">> Module : Restore retired/lost players              <<" -foregroundcolor yellow
            write-host ">>>>>>>>>>>>>>>>>>>>>>>>>>>>><<<<<<<<<<<<<<<<<<<<<<<<<<<" -foregroundcolor yellow
            write-host ">> [1] : Type the Playername, to restore              <<" -foregroundcolor white
            write-host ">> [M] : Back to Menu                                 <<" -foregroundcolor white
            write-host ">> [x] : Exit                                         <<" -foregroundcolor white
            write-host ">>>>>>>>>>>>>>>>>>>>>>>>>>>>><<<<<<<<<<<<<<<<<<<<<<<<<<<" -foregroundcolor yellow
            write-host ">> Type the Playername, without xxRETIRED_, which it  <<" -foregroundcolor green
            write-host ">> is in your players.csv - Example xxRETIREDxx_Hanna <<" -foregroundcolor green
            write-host ">> than type only Hanna. The player get restored in   <<" -foregroundcolor green
            write-host ">> the player.csv and into your working-database.     <<" -foregroundcolor green
            write-host ">>>>>>>>>>>>>>>>>>>>>>>>>>>>><<<<<<<<<<<<<<<<<<<<<<<<<<<" -foregroundcolor yellow
            write-host ""
            write-host ""

            $input = Read-Host "Find [1] ?"
            $find = ": xxRETIREDxx_" + $input
            $find_a = "Source"
            $find_b = "xxRETIREDxx_" + $input
            $rename = ": " + $input
            $rename_b = $input

            if ($input -eq 'x' -or $inpur -eq 'X')
            {write-host ""
            write-host "-- EXIT --"
            write-host ""
            Start-Sleep -Milliseconds 2000
            [System.Environment]::Exit(0)
            break}

            if ($input -eq 'M' -or $input -eq 'm')
            {write-host ""
            Start-Sleep -Milliseconds 2000
            & ".\tb-c1-en.ps1"}            

                # Working Archive
                $a = 0
                $a1 = 0
                $a2 = 0
                $z = 0
                $z1 = 0
                $z2 = 0
                clear-host
                Start-Sleep -Milliseconds 100
                write-host ""
                write-host ""
                write-host ">>>>>>>>>>>>>>>>>>>>>>>>>>>>><<<<<<<<<<<<<<<<<<<<<<<<<<<" -foregroundcolor green
                write-host "> Find Player $input and remove xxRETIREDxx             " -foregroundcolor yellow
                write-host "> If you have a large database, the process may take    " -foregroundcolor yellow
                write-host "> some time. The process can run in the background,     " -foregroundcolor yellow
                write-host "> that allowing you to perform other tasks in parallel. " -foregroundcolor yellow
                write-host ">>>>>>>>>>>>>>>>>>>>>>>>>>>>><<<<<<<<<<<<<<<<<<<<<<<<<<<" -foregroundcolor green
                write-host ""
                Start-Sleep -Milliseconds 16000

                # -------------------------------------------
                # Alle .txt Dateien im Ordner Working abrufen
                # -------------------------------------------
                Get-ChildItem -Path $working -Filter "*.txt" | ForEach-Object {
                $a += 1
                $file = $_
                $content = Get-Content -Path $file.FullName

                write-host ">>>>> Process Working File : $a" -foregroundcolor yellow

                # Save Inhalt in eine temp Variable
                $newcontent = @()

                    # Alle Zeilen durchsuchen
                    for ($i = 0; $i -lt $content.Length; $i++) {
                        $currentrow = $content[$i]

                        # Überprüfen, ob die aktuelle Zeile das zu suchende Wort enthält
                        if ($currentrow -like "*$find") {
                        # Überprüfen, ob es eine nächste Zeile gibt
                        if ($i + 1 -lt $content.Length) {
                        $nextrow = $content[$i + 1]

                        # Überprüfen, ob die nächste Zeile das Source-Wort enthält
                        if ($nextrow -like "$find_a*") {
                            # Zeile mit dem Eingabewort ersetzen
                            $newcontent += $currentrow -replace $find, $rename
                            $z += 1

                        } else {
                            # Keine Treffer
                            $newcontent += $currentrow
                        }
                    
                        } else {
                        # Keine nächste Zeile vorhanden
                        $newcontent += $currentrow
                        }
                    
                        } else {
                        # Zeile, die das Wort nicht enthält, unverändert lassen
                        $newcontent += $currentrow
                        }
                    }

                # Den neuen Inhalt zurück in die Datei schreiben
                $newcontent | Set-Content -Path $file.FullName
                }

                # -------------------------------------------
                # Alle .txt Dateien im Archive Ordner abrufen
                # -------------------------------------------
                Get-ChildItem -Path $archive -Filter "*.archive" | ForEach-Object {
                $a2 += 1
                $file = $_
                $content = Get-Content -Path $file.FullName

                write-host ">>>>> Process Archive File : $a2" -foregroundcolor yellow

                # Save Inhalt in eine temp Variable
                $newcontent = @()

                    # Alle Zeilen durchsuchen
                    for ($i = 0; $i -lt $content.Length; $i++) {
                        $currentrow = $content[$i]

                        # Überprüfen, ob die aktuelle Zeile das zu suchende Wort enthält
                        if ($currentrow -like "*$find") {
                        # Überprüfen, ob es eine nächste Zeile gibt
                        if ($i + 1 -lt $content.Length) {
                        $nextrow = $content[$i + 1]

                        # Überprüfen, ob die nächste Zeile das Source-Wort enthält
                        if ($nextrow -like "$find_a*") {
                            # Zeile mit dem Eingabewort ersetzen
                            $newcontent += $currentrow -replace $find, $rename
                            $z2 += 1

                        } else {
                            # Keine Treffer
                            $newcontent += $currentrow
                        }
                    
                        } else {
                        # Keine nächste Zeile vorhanden
                        $newcontent += $currentrow
                        }
                    
                        } else {
                        # Zeile, die das Wort nicht enthält, unverändert lassen
                        $newcontent += $currentrow
                        }
                    }

                # Den neuen Inhalt zurück in die Datei schreiben
                $newcontent | Set-Content -Path $file.FullName
                }

                # ----------------------------------------
                # Alle .txt Dateien im Data Ordner abrufen
                # ----------------------------------------
                Get-ChildItem -Path $dpath -Filter "*c1.txt" | ForEach-Object {
                $a1 += 1
                $file = $_
                $content = Get-Content -Path $file.FullName

                write-host ">>>>> Process Data File : $a1" -foregroundcolor yellow

                # Save Inhalt in eine temp Variable
                $newcontent = @()

                    # Alle Zeilen durchsuchen
                    for ($i = 0; $i -lt $content.Length; $i++) {
                        $currentrow = $content[$i]

                        # Überprüfen, ob die aktuelle Zeile das zu suchende Wort enthält
                        if ($currentrow -like "*$find") {
                        # Überprüfen, ob es eine nächste Zeile gibt
                        if ($i + 1 -lt $content.Length) {
                        $nextrow = $content[$i + 1]

                        # Überprüfen, ob die nächste Zeile das Source-Wort enthält
                        if ($nextrow -like "$find_a*") {
                            # Zeile mit dem Eingabewort ersetzen
                            $newcontent += $currentrow -replace $find, $rename
                            $z1 += 1

                        } else {
                            # Keine Treffer
                            $newcontent += $currentrow
                        }
                    
                        } else {
                        # Keine nächste Zeile vorhanden
                        $newcontent += $currentrow
                        }
                    
                        } else {
                        # Zeile, die das Wort nicht enthält, unverändert lassen
                        $newcontent += $currentrow
                        }
                    }

                # Den neuen Inhalt zurück in die Datei schreiben
                $newcontent | Set-Content -Path $file.FullName
                }

                clear-host
                Start-Sleep -Milliseconds 100
                write-host ""
                write-host ""
                write-host ">>>>>>>>>>>>>>>>>>>>>>>>>>>>><<<<<<<<<<<<<<<<<<<<<<<<<<<" -foregroundcolor green
                write-host "> Player $input get restored                            " -foregroundcolor yellow
                write-host ">>>>>>>>>>>>>>>>>>>>>>>>>>>>><<<<<<<<<<<<<<<<<<<<<<<<<<<" -foregroundcolor green
                write-host ""
                write-host ">>>>> Process Working Files    : $a" -foregroundcolor yellow
                write-host ">>>>> Process Archive Files    : $a2" -foregroundcolor yellow
                write-host ">>>>> Process Data Files       : $a1" -foregroundcolor yellow
                
                if ($z -gt 0){write-host ">>>>> Restored Player @Working : $z" -foregroundcolor yellow}
                if ($z2 -gt 0){write-host ">>>>> Restored Player @Archive : $z2" -foregroundcolor yellow}
                if ($z1 -gt 0){write-host ">>>>> Restored Player @Data    : $z1" -foregroundcolor yellow}
                if ($z -lt 1){write-host ">>>>> Player xxRETIREDxx_$input not found @Working" -foregroundcolor yellow}
                if ($z2 -lt 1){write-host ">>>>> Player xxRETIREDxx_$input not found @Archive" -foregroundcolor yellow}
                if ($z1 -lt 1){write-host ">>>>> Player xxRETIREDxx_$input not found @Data" -foregroundcolor yellow}
                
                # Prüfen, ob das exakte Wort in der Datei vorhanden ist
                # \b steht für eine Wortgrenze, um nur das Wort zu finden
                $playerexists = Select-String -Path $players -Pattern "$find_b\b" -Quiet

                if ($playerexists) {
                    $content = Get-Content -Path $players -Raw
                    $newcontent = $content -creplace "\b$find_b\b", $rename_b
                    Set-Content -Path $players -Value $newcontent
                        # Read, sort, delete empty rows and write Player.csv back
                        $content = Get-Content -Path $players
                        $contentfilter = $content | Where-Object {$_.Trim() -ne ""}
                        $sort = $contentfilter | Sort-Object
                        $sort | Set-Content -Path $players
                } else {
                    Write-Host ""
                    Write-Host ">>>>> Oooops:                            " -foregroundcolor white
                    Write-Host ">>>>> The Player '$input'                " -foregroundcolor white
                    Write-Host ">>>>> was not found into the players.csv " -foregroundcolor white
                    Write-Host ">>>>> it can happen, if there is no      " -foregroundcolor white
                    write-host ">>>>> aliasses => please check manually  " -foregroundcolor white
                }

                write-host ""
                write-host ">>>>>>>>>>>>>>>>>>>>>>>>>>>>><<<<<<<<<<<<<<<<<<<<<<<<<<<" -foregroundcolor yellow
                write-host ">>> PROCESS COMPLETED - CHECK your players.csv       <<<" -foregroundcolor yellow
                write-host ">>>>>>>>>>>>>>>>>>>>>>>>>>>>><<<<<<<<<<<<<<<<<<<<<<<<<<<" -foregroundcolor yellow
                write-host ""
                Start-Sleep -Milliseconds 3000
                write-host ""
                write-host ""
                write-host ">>>>>>>>>>>>>>>>>>>>>>>><<<<<<<<<<<<<<<<<<<<<" -foregroundcolor yellow
                write-host ">>> E[x]it or type another Key for [M]enu <<<" -foregroundcolor yellow
                write-host ">>>>>>>>>>>>>>>>>>>>>>>><<<<<<<<<<<<<<<<<<<<<" -foregroundcolor yellow
                write-host ""
                    # Play with ANY-KEY :D
                    $input = Read-Host " [X] or [ANY-KEY] ? "
                    if ($input -eq 'x' -or $input -eq 'X')
                        {write-host ""
                        write-host "-- EXIT --"
                        write-host ""
                        Start-Sleep -Milliseconds 2000
                        [System.Environment]::Exit(0)
                        break}
                    else
                        {write-host ""
                        write-host "-- ANY-KEY --"
                        write-host ""
                        Start-Sleep -Milliseconds 3000
                        & ".\tb-c1-en.ps1"}
        }

    elseif ($value -eq 'S' -or $value -eq "s")
        {
            # Sort in alphabetical order all players.csv
            Clear-Host
            Start-Sleep -Milliseconds 250
            write-host ""
            write-host ">>>>>>>>>>>>>>>>>>>>><<<<<<<<<<<<<<<<<<<" -foregroundcolor yellow
            write-host ">> Please wait, while we sort now in  <<" -foregroundcolor white
            write-host ">> alphabetical oder your players.csv <<" -foregroundcolor white
            write-host ">> Empty Lines get also removed       <<" -foregroundcolor white
            write-host ">>>>>>>>>>>>>>>>>>>>><<<<<<<<<<<<<<<<<<<" -foregroundcolor yellow
            # Read, sort, delete empty rows and write players.csv back
            $content = Get-Content -Path $players
            $contentfilter = $content | Where-Object {$_.Trim() -ne ""}
            $sort = $contentfilter | Sort-Object
            $sort | Set-Content -Path $players
            # Read, sort, delete empty rows and write players_c2.csv back
            $content = Get-Content -Path $players_c2
            $contentfilter = $content | Where-Object {$_.Trim() -ne ""}
            $sort = $contentfilter | Sort-Object
            $sort | Set-Content -Path $players_c2
            # Read, sort, delete empty rows and write players_c3.csv back
            $content = Get-Content -Path $players_c3
            $contentfilter = $content | Where-Object {$_.Trim() -ne ""}
            $sort = $contentfilter | Sort-Object
            $sort | Set-Content -Path $players_c3
            # Read, sort, delete empty rows and write players_c4.csv back
            $content = Get-Content -Path $players_c4
            $contentfilter = $content | Where-Object {$_.Trim() -ne ""}
            $sort = $contentfilter | Sort-Object
            $sort | Set-Content -Path $players_c4
            Start-Sleep -Milliseconds 5000
            write-host ">> All Players.csv processed / done   <<" -foregroundcolor yellow
            write-host ">>>>>>>>>>>>>>>>>>>>><<<<<<<<<<<<<<<<<<<" -foregroundcolor yellow
            Start-Sleep -Milliseconds 5000
            & ".\tb-c1-en.ps1"
        }
    elseif ($value -eq 'i' -or $value -eq "I")
        {
            # Show Install-Instruction
            Clear-Host
            Start-Sleep -Milliseconds 250
            write-host ""
            $path = $main + "INSTALL.txt"
            Get-Content -Path $path -Raw | Write-Host
                    # Play with ANY-KEY :D
                    $input = Read-Host " Ready ? "
                    if ($input -eq 'x' -or $input -eq 'X')
                        {write-host ""
                        write-host "-- EXIT --"
                        write-host ""
                        Start-Sleep -Milliseconds 2000
                        [System.Environment]::Exit(0)
                        break}
                    else
                        {Start-Sleep -Milliseconds 2000
                        & ".\tb-c1-en.ps1"}
        }

    elseif ($value -eq 'y' -or $value -eq "Y")
        {
            # Show YT-Video
            Start-Process "https://youtu.be/CDKj89Oo2gM"
            Start-Sleep -Milliseconds 2000
            & ".\tb-c1-en.ps1"
        }
	elseif ($value -eq 'p' -or $value -eq "P")
        {
            # Install new Pwsh Version
            Clear-Host
            write-host ""
            write-host ">>>>>>>>>>>>>>>>>>>>><<<<<<<<<<<<<<<<<<<" -foregroundcolor yellow
            write-host ">> Please wait, try update Powershell <<" -foregroundcolor white
            write-host ">>>>>>>>>>>>>>>>>>>>><<<<<<<<<<<<<<<<<<<" -foregroundcolor yellow
            write-host ""
            write-host ""
			& winget install --id Microsoft.Powershell --source winget
            Start-Sleep -Milliseconds 5000
            & ".\tb-c1-en.ps1"
		}
	elseif ($value -eq 'v' -or $value -eq "V")
        {
            # Version from Python
            Clear-Host
            write-host ""
            write-host ">>>>>>>>>>>>>>>>>>>>><<<<<<<<<<<<<<<<<<<" -foregroundcolor yellow
            write-host ">>    Your current Python Version     <<" -foregroundcolor white
            write-host ">>>>>>>>>>>>>>>>>>>>><<<<<<<<<<<<<<<<<<<" -foregroundcolor yellow
            write-host ""
            py --version
            write-host ""
            Start-Sleep -Milliseconds 5000
            & ".\tb-c1-en.ps1"
		}
elseif ($value -eq 'c' -or $value -eq "C")
        {   $image = $main + "config\TBCalibration-How2.png"
            # Show Wiki Site for Updates
            Start-Process $image
            Start-Sleep -Milliseconds 2000
            & ".\tb-c1-en.ps1"
        }        
elseif ($value -eq 'u' -or $value -eq "U")
        {
            # Show Wiki Site for Updates
            Start-Process "https://dragon-wiki.com/doku.php?id=clanchestcounter"
            Start-Sleep -Milliseconds 2000
            & ".\tb-c1-en.ps1"
        }        
    else {write-host ""
        write-host "Wrong Input"
        Start-Sleep -Milliseconds 3000
        & ".\tb-c1-en.ps1"}