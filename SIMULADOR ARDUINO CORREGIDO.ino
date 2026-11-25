const byte ledsCompartidos[4] = {22, 23, 24, 25};
const byte buzzerS2 = 34;
const int notasS2[4] = {262, 330, 392, 523};
const byte secuenciaS2[4] = {0, 2, 1, 3};

const byte potR = A0;
const byte potG = A1;
const byte potB = A2;
const byte rgbJugador[3] = {2, 3, 4};
const bool rgbAnodoComun = false;
const int toleranciaRGB = 30;

const byte botonPuntoS4 = 35;
const byte botonRayaS4 = 36;
const byte buzzerS4 = 37;

const char letrasMorse[] = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
const char* diccionarioMorse[26] = {
  ".-", "-...", "-.-.", "-..", ".", "..-.", "--.", "....", "..", ".---",
  "-.-", ".-..", "--", "-.", "---", ".--.", "--.-", ".-.", "...", "-",
  "..-", "...-", ".--", "-..-", "-.--", "--.."
};

struct Pulsador {
  byte pin;
  bool anterior;
  bool estable;
  unsigned long ultimoCambio;
};

// Los mismos cuatro botones sirven para Memoria y Musical.
Pulsador botonesCompartidos[4] = {
  {26, HIGH, HIGH, 0}, {27, HIGH, HIGH, 0},
  {28, HIGH, HIGH, 0}, {29, HIGH, HIGH, 0}
};

Pulsador puntoS4 = {35, HIGH, HIGH, 0};
Pulsador rayaS4 = {36, HIGH, HIGH, 0};

byte secuenciasS1[100][8];
byte numeroS1 = 0;
byte indiceLucesS1 = 0;
byte indiceRespuestaS1 = 0;
byte parpadeosS1 = 0;
unsigned long marcaS1 = 0;

enum FaseS1 {
  S1_LUZ_ENCENDIDA, S1_LUZ_APAGADA, S1_RESPONDER,
  S1_REINTENTAR, S1_PARPADEO_ENCENDIDO, S1_PARPADEO_APAGADO, S1_TERMINADO
};
FaseS1 faseS1 = S1_LUZ_ENCENDIDA;

byte indiceMelodiaS2 = 0;
byte indiceRespuestaS2 = 0;
byte notaPendienteS2 = 0;
bool respuestaCorrectaS2 = false;
unsigned long marcaS2 = 0;

enum FaseS2 {
  S2_ESPERAR_S1, S2_PREPARAR_MELODIA, S2_SONANDO_MELODIA, S2_PAUSA,
  S2_RESPONDER, S2_PREPARAR_RESPUESTA, S2_SONANDO_RESPUESTA,
  S2_REINTENTAR, S2_TERMINADO
};
FaseS2 faseS2 = S2_ESPERAR_S1;

int objetivoRGB[3] = {0, 0, 0};
int estadoAnteriorRGB = -1;
int colorAnteriorRGB[3] = {-1, -1, -1};
bool completoS3 = false;
unsigned long ultimaLecturaRGB = 0;

String palabraS4 = "";
String objetivoMorseS4 = "";
String entradaMorseS4 = "";
bool completoS4 = false;

int pinTonoActivo = -1;
unsigned long inicioTono = 0;
unsigned long duracionTono = 0;

bool pulsacion(Pulsador &boton, unsigned long ahora) {
  bool lectura = digitalRead(boton.pin);
  if (lectura != boton.anterior) boton.ultimoCambio = ahora;
  boton.anterior = lectura;

  if (lectura != boton.estable && ahora - boton.ultimoCambio >= 30) {
    boton.estable = lectura;
    return lectura == LOW;
  }
  return false;
}

bool solicitarTono(byte pin, int frecuencia, unsigned long duracion, unsigned long ahora) {
  if (pinTonoActivo != -1) return false;
  tone(pin, frecuencia);
  pinTonoActivo = pin;
  inicioTono = ahora;
  duracionTono = duracion;
  return true;
}

void actualizarTono(unsigned long ahora) {
  if (pinTonoActivo != -1 && ahora - inicioTono >= duracionTono) {
    noTone(pinTonoActivo);
    digitalWrite(pinTonoActivo, HIGH); // Reposo: modulo activo en LOW.
    pinTonoActivo = -1;
  }
}

void comenzarS1(unsigned long ahora) {
  numeroS1 = random(0, 100);
  indiceLucesS1 = 0;
  indiceRespuestaS1 = 0;
  faseS1 = S1_LUZ_ENCENDIDA;
  marcaS1 = ahora;
  digitalWrite(ledsCompartidos[secuenciasS1[numeroS1][0]], HIGH);
  Serial.println("S1:START:8");
}

void actualizarS1(unsigned long ahora, const bool eventos[4]) {
  switch (faseS1) {
    case S1_LUZ_ENCENDIDA:
      if (ahora - marcaS1 >= 600) {
        digitalWrite(ledsCompartidos[secuenciasS1[numeroS1][indiceLucesS1]], LOW);
        faseS1 = S1_LUZ_APAGADA;
        marcaS1 = ahora;
      }
      break;

    case S1_LUZ_APAGADA:
      if (ahora - marcaS1 >= 400) {
        indiceLucesS1++;
        if (indiceLucesS1 == 8) {
          faseS1 = S1_RESPONDER;
          Serial.println("S1:READY:1");
        } else {
          digitalWrite(ledsCompartidos[secuenciasS1[numeroS1][indiceLucesS1]], HIGH);
          faseS1 = S1_LUZ_ENCENDIDA;
          marcaS1 = ahora;
        }
      }
      break;

    case S1_RESPONDER:
      for (byte i = 0; i < 4; i++) {
        if (!eventos[i]) continue;
        if (i == secuenciasS1[numeroS1][indiceRespuestaS1]) {
          indiceRespuestaS1++;
          Serial.print("S1:STEP:");
          Serial.println(int(indiceRespuestaS1));
          if (indiceRespuestaS1 == 8) {
            Serial.println("S1:COMPLETE:1");
            parpadeosS1 = 0;
            for (byte j = 0; j < 4; j++) digitalWrite(ledsCompartidos[j], HIGH);
            faseS1 = S1_PARPADEO_ENCENDIDO;
            marcaS1 = ahora;
          }
        } else {
          Serial.println("S1:FAIL:0");
          faseS1 = S1_REINTENTAR;
          marcaS1 = ahora;
        }
        break;
      }
      break;

    case S1_REINTENTAR:
      if (ahora - marcaS1 >= 2000) comenzarS1(ahora);
      break;

    case S1_PARPADEO_ENCENDIDO:
      if (ahora - marcaS1 >= 300) {
        for (byte j = 0; j < 4; j++) digitalWrite(ledsCompartidos[j], LOW);
        faseS1 = S1_PARPADEO_APAGADO;
        marcaS1 = ahora;
      }
      break;

    case S1_PARPADEO_APAGADO:
      if (ahora - marcaS1 >= 200) {
        parpadeosS1++;
        if (parpadeosS1 == 3) {
          faseS1 = S1_TERMINADO;
        } else {
          for (byte j = 0; j < 4; j++) digitalWrite(ledsCompartidos[j], HIGH);
          faseS1 = S1_PARPADEO_ENCENDIDO;
          marcaS1 = ahora;
        }
      }
      break;

    case S1_TERMINADO:
      break;
  }
}

void actualizarS2(unsigned long ahora, const bool eventos[4]) {
  switch (faseS2) {
    case S2_ESPERAR_S1:
      if (faseS1 == S1_TERMINADO) {
        indiceMelodiaS2 = 0;
        indiceRespuestaS2 = 0;
        Serial.println("S2:START:4");
        faseS2 = S2_PREPARAR_MELODIA;
      }
      break;

    case S2_PREPARAR_MELODIA:
      if (solicitarTono(buzzerS2, notasS2[secuenciaS2[indiceMelodiaS2]], 350, ahora)) {
        digitalWrite(ledsCompartidos[secuenciaS2[indiceMelodiaS2]], HIGH);
        marcaS2 = ahora;
        faseS2 = S2_SONANDO_MELODIA;
      }
      break;

    case S2_SONANDO_MELODIA:
      if (ahora - marcaS2 >= 350) {
        digitalWrite(ledsCompartidos[secuenciaS2[indiceMelodiaS2]], LOW);
        marcaS2 = ahora;
        faseS2 = S2_PAUSA;
      }
      break;

    case S2_PAUSA:
      if (ahora - marcaS2 >= 200) {
        indiceMelodiaS2++;
        if (indiceMelodiaS2 == 4) {
          faseS2 = S2_RESPONDER;
          Serial.println("S2:READY:1");
        } else {
          faseS2 = S2_PREPARAR_MELODIA;
        }
      }
      break;

    case S2_RESPONDER:
      for (byte i = 0; i < 4; i++) {
        if (!eventos[i]) continue;
        notaPendienteS2 = i;
        respuestaCorrectaS2 = i == secuenciaS2[indiceRespuestaS2];
        if (respuestaCorrectaS2) {
          indiceRespuestaS2++;
          Serial.print("S2:STEP:");
          Serial.println(int(indiceRespuestaS2));
        } else {
          Serial.println("S2:FAIL:0");
        }
        faseS2 = S2_PREPARAR_RESPUESTA;
        break;
      }
      break;

    case S2_PREPARAR_RESPUESTA:
      if (solicitarTono(buzzerS2, notasS2[notaPendienteS2], 180, ahora)) {
        digitalWrite(ledsCompartidos[notaPendienteS2], HIGH);
        marcaS2 = ahora;
        faseS2 = S2_SONANDO_RESPUESTA;
      }
      break;

    case S2_SONANDO_RESPUESTA:
      if (ahora - marcaS2 >= 180) {
        digitalWrite(ledsCompartidos[notaPendienteS2], LOW);
        if (!respuestaCorrectaS2) {
          indiceRespuestaS2 = 0;
          faseS2 = S2_REINTENTAR;
          marcaS2 = ahora;
        } else if (indiceRespuestaS2 == 4) {
          faseS2 = S2_TERMINADO;
          Serial.println("S2:COMPLETE:1");
        } else {
          faseS2 = S2_RESPONDER;
        }
      }
      break;

    case S2_REINTENTAR:
      if (ahora - marcaS2 >= 600) {
        indiceMelodiaS2 = 0;
        faseS2 = S2_PREPARAR_MELODIA;
        Serial.println("S2:RETRY:1");
      }
      break;

    case S2_TERMINADO:
      break;
  }
}

void actualizarS3(unsigned long ahora) {
  if (completoS3 || ahora - ultimaLecturaRGB < 100) return;
  ultimaLecturaRGB = ahora;

  int valores[3] = {
    int(map(analogRead(potR), 0, 1023, 0, 255)),
    int(map(analogRead(potG), 0, 1023, 0, 255)),
    int(map(analogRead(potB), 0, 1023, 0, 255))
  };

  int estados[3];
  bool cambioColor = false;
  for (byte i = 0; i < 3; i++) {
    analogWrite(rgbJugador[i], rgbAnodoComun ? 255 - valores[i] : valores[i]);
    estados[i] = abs(valores[i] - objetivoRGB[i]) <= toleranciaRGB ? 1 : 0;
    if (valores[i] != colorAnteriorRGB[i]) cambioColor = true;
    colorAnteriorRGB[i] = valores[i];
  }

  // El color objetivo solo se muestra en CustomTkinter: no existe otro LED.
  if (cambioColor) {
    Serial.print("S3:COLOR:");
    Serial.print(valores[0]);
    Serial.print(",");
    Serial.print(valores[1]);
    Serial.print(",");
    Serial.println(valores[2]);
  }

  int mascara = estados[0] * 4 + estados[1] * 2 + estados[2];
  if (mascara != estadoAnteriorRGB) {
    Serial.print("S3:RGB:");
    Serial.print(estados[0]);
    Serial.print(",");
    Serial.print(estados[1]);
    Serial.print(",");
    Serial.println(estados[2]);
    estadoAnteriorRGB = mascara;
  }

  if (mascara == 7) {
    completoS3 = true;
    Serial.println("S3:COMPLETE:1");
  }
}

void registrarMorse(char simbolo) {
  if (completoS4) return;

  unsigned int posicion = entradaMorseS4.length();
  if (posicion >= objetivoMorseS4.length() || simbolo != objetivoMorseS4[posicion]) {
    entradaMorseS4 = "";
    Serial.println("S4:FAIL:0");
    return;
  }

  entradaMorseS4 += simbolo;
  Serial.print("S4:STEP:");
  Serial.println(entradaMorseS4.length());

  if (entradaMorseS4 == objetivoMorseS4) {
    completoS4 = true;
    Serial.println("S4:COMPLETE:1");
  }
}

void actualizarS4(unsigned long ahora, bool punto, bool raya) {
  if (completoS4) return;
  if (punto) {
    solicitarTono(buzzerS4, 1000, 120, ahora);
    registrarMorse('.');
  } else if (raya) {
    solicitarTono(buzzerS4, 500, 240, ahora);
    registrarMorse('-');
  }
}

void setup() {
  Serial.begin(9600);

  for (byte i = 0; i < 4; i++) {
    pinMode(ledsCompartidos[i], OUTPUT);
    pinMode(botonesCompartidos[i].pin, INPUT_PULLUP);
  }
  digitalWrite(buzzerS2, HIGH); // Preparar nivel de reposo antes de habilitar salida.
  pinMode(buzzerS2, OUTPUT);
  pinMode(botonPuntoS4, INPUT_PULLUP);
  pinMode(botonRayaS4, INPUT_PULLUP);
  digitalWrite(buzzerS4, HIGH); // Preparar nivel de reposo antes de habilitar salida.
  pinMode(buzzerS4, OUTPUT);

  for (byte i = 0; i < 3; i++) {
    pinMode(rgbJugador[i], OUTPUT);
  }

  randomSeed(analogRead(A15) + micros());

  for (byte i = 0; i < 100; i++) {
    for (byte j = 0; j < 8; j++) {
      secuenciasS1[i][j] = random(0, 4);
    }
  }

  for (byte i = 0; i < 3; i++) {
    objetivoRGB[i] = random(0, 256);
  }

  for (byte i = 0; i < 4; i++) {
    byte indice = random(0, 26);
    palabraS4 += letrasMorse[indice];
    objetivoMorseS4 += diccionarioMorse[indice];
  }

  Serial.println("S3:START:1");
  Serial.print("S3:TARGET:");
  Serial.print(objetivoRGB[0]);
  Serial.print(",");
  Serial.print(objetivoRGB[1]);
  Serial.print(",");
  Serial.println(objetivoRGB[2]);
  Serial.print("S4:TARGET:");
  Serial.println(palabraS4);
  comenzarS1(millis());
}

void loop() {
  unsigned long ahora = millis();
  actualizarTono(ahora);

  bool eventosCompartidos[4];
  for (byte i = 0; i < 4; i++) {
    eventosCompartidos[i] = pulsacion(botonesCompartidos[i], ahora);
  }
  bool eventoPunto = pulsacion(puntoS4, ahora);
  bool eventoRaya = pulsacion(rayaS4, ahora);

  // Musical permanece bloqueado hasta finalizar Memoria y su parpadeo final.
  actualizarS1(ahora, eventosCompartidos);
  actualizarS2(ahora, eventosCompartidos);
  actualizarS3(ahora);
  actualizarS4(ahora, eventoPunto, eventoRaya);
}
