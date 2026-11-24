PROYECTO: DESACTIVA LA BOMBA!!  ---  ESTUDIANTES: GARCIA,Lucca - OLLER,Benjamin - MONSERRAT,Fausto  ---  CURSO: 4TO "C"  ---  MATERIA: PROGRAMACION I  ---  CICLO LECTIVO: 2026

DESCRIPCION GENERAL:
El proyecto consiste en desarrollar un juego interactivo de desactivación de una bomba ficticia, utilizando una placa Arduino Mega como controlador principal y Python con Tkinter para crear una interfaz gráfica que acompañe la partida.
El dispositivo estará dividido en cuatro sectores independientes, cada uno con un desafío diferente que el jugador deberá superar antes de que termine el tiempo. Cada sector tendrá tres variantes posibles, seleccionadas aleatoriamente al comenzar cada partida.

DESCRIPCION DE LOS SECTORES:
Sector 1 – Memoria y secuencia de luces: El jugador deberá observar y repetir secuencias de luces mediante pulsadores, inspirado en el juego Simón dice. Tendrá tres variantes.
Sector 2 – Desafío musical: El jugador deberá reproducir melodías utilizando cuatro pulsadores y buzzers. Tendrá tres melodías posibles.
Sector 3 – Combinación de colores: Se utilizarán tres potenciómetros RGB para formar el color objetivo que aparecerá en la interfaz gráfica. Tendrá tres colores posibles.
Sector 4 – Código Morse: El jugador deberá interpretar y reproducir palabras de cuatro caracteres mediante pulsadores. Tendrá tres palabras posibles.

SISTEMA DE PENALIZACION:
El jugador deberá completar los cuatro desafíos dentro del tiempo establecido. Si no lo consigue, la partida finalizará con un resultado negativo y con una aviso en una ventana de tkinter.

OBJETIVOS DEL PROYECTO:
Integrar programación, electrónica e interfaces gráficas mediante Arduino Mega y Python con Tkinter, creando un juego interactivo que ponga a prueba la memoria, la coordinación y la capacidad de resolución de problemas.

INTERFAZ GRAFICA EN PHYTON (Tkinter): La interfaz gráfica será el centro de información y control del juego. Se comunicará con Arduino Mega mediante comunicación serial.
   La interfaz deberá mostrar:
    ELEMENTO         FUNCIONALIDAD
    Cronómetro ----> Mostrar el tiempo restante de la partida.
    Explicaciones -> Indicar las instrucciones del desafío actual.
    Estado de sectores ---> Mostrar si cada sector está pendiente o completado.
    Variante aleatoria ----> Indicar cuál de las tres variantes fue seleccionada para cada sector.
    Progreso general ---> Mostrar cuántos de los cuatro sectores fueron completados.
    Resultado ---> Indicar si la misión fue completada o fallida.

 Además, cuando se seleccione un desafío, Tkinter mostrará las instrucciones correspondientes y actualizará su estado en tiempo real según las respuestas recibidas desde Arduino.

 COMUNICACION SERIAL: La comunicación será entre Arduino Mega y Python. Los datos exactos y el formato de mensajes se definirán durante la implementación.
     ARDUINO → PYTHON: Lecturas de pulsadores y potenciómetros, entradas de secuencia/melodía/Morse y estados necesarios para validar los desafíos.
     PYTHON → ARDUINO: Órdenes de inicio, selección de variantes y control de actuadores (luces, sonidos y efecto final), según la lógica del juego.

COMO EJECUTAR EL PROYECTO?

 1) INSTALAR PROGRAMAS
- Arduino IDE.
- Python 3.
- Visual Studio Code.

2) INSTALAR LIBRERIAS DE PHYTON
Abrir la terminal y ejecutar:
   pip install pyserial
Tkinter generalmente viene incluido con Python.

3) CARGAR EL CODIGO EN ARDUINO
1. Conectar Arduino Mega mediante USB.
2. Abrir el archivo `.ino` en Arduino IDE.
3. Seleccionar la placa Arduino Mega 2560 y el puerto COM correspondiente.
4. Presionar Verificar y luego Subir.

4) EJECUTAR EL JUEGO
1. Abrir la carpeta del proyecto en Visual Studio Code.
2. Conectar Arduino a la computadora.
3. Ejecutar el archivo principal de Python.
4. Esperar a que aparezca la interfaz gráfica de Tkinter.
5. Iniciar la partida.

5) FINALIZACION
El jugador deberá completar los cuatro desafíos antes de que termine el tiempo para conseguir la misión exitosa.


6) COMPONENTES A UTILIZAR:
   1 placa Arduino Mega 2560.
   4 LEDs individuales.
   1 LED RGB.
   6 pulsadores.
   3 potenciómetros.
   2 buzzers.
   4 resistencias para los LEDs.
   1 protoboard.
   Cables jumper macho-macho.
   1 cable USB para Arduino.

NOTA: EL UNICO CAMBIO FUE REMPLAZAR EL USO DEL SERVOMOTOR PARA LA EXPLOSION DEL GLOBO, EN CASO DE FRACASAR (YA QUE LO CONSIDERAMOS PELIGROSO Y COMPLICACIONES DE MAS INECESARIAS). ADEMAS DE ESTO, NO HUBIERON CAMBIOS EN LA REALIZACION DEL PROYECTO, TENIENDO EN CUENTA LO REDACTADO EN EL ANTEPROYECTO DEL TP.
