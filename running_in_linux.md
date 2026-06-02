
1. Installa Xephyr se non c’è:
	
	sudo apt install xserver-xephyr

2. Apri un primo terminale e avvia il server X annidato:
	
	Xephyr :99 -screen 1280x800 -ac -br -reset

3. Apri un secondo terminale e avvia l’app su quel display:
	
	DISPLAY=:99 /home/ubu/PycharmProjects/Josm_Tagger/.venv/bin/python /home/ubu/PycharmProjects/Josm_Tagger/main.py

4. Se vuoi usare lo script del progetto invece del comando manuale:
	
	JOSM_TAGGER_USE_XEPHYR=1 ./josmtagger.sh

5. Verifica che la finestra dell’app sia dentro la finestra di Xephyr, non nel desktop Wayland normale.
   Se vuoi una sessione X11 vera invece di Xephyr:

	echo $XDG_SESSION_TYPE

  deve restiture x11, e in quel caso puoi lanciare normalmente ./josmtagger.sh.
