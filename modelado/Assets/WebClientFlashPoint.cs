using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Networking;
using TMPro;

[System.Serializable]
public class AgentData
{
    public int id;
    public int x;
    public int y;
    public bool carrying_victim;
    public bool is_knocked_down;
    public int current_ap;
    public int saved_ap;
}

[System.Serializable]
public class FireData
{
    public int x;
    public int y;
    public int state;
}

[System.Serializable]
public class PoiData
{
    public int x;
    public int y;
    public bool revealed;
    public string type;
}

[System.Serializable]
public class DamageData
{
    public int x1;
    public int y1;
    public int x2;
    public int y2;
    public string type;
    public bool destroyed;
}

[System.Serializable]
public class GameState
{
    public int turn;
    public bool game_over;
    public bool win;
    public int structural_damage;
    public int victims_rescued;
    public int victims_lost;
    public AgentData[] agents;
    public FireData[] fires;
    public PoiData[] pois;
    public DamageData[] damages;
}

public class WebClientFlashPoint : MonoBehaviour
{
    [Header("UI")]
    public TMP_Text textoRescatadas;
    public TMP_Text textoPerdidas;
    public TMP_Text textoDanio;
    public TMP_Text textoTurno;
    public TMP_Text textoAgentes;
    public GameObject panelFinal;
    public TMP_Text textoFinal;

    [Header("Configuración del Servidor")]
    public string serverUrl = "http://localhost:8585";

    [Header("Ajustes del Tablero")]
    public float gridScale = 2.0f;
    [Tooltip("Coordenada XYZ real en Unity donde se ubica la casilla (0,0) lógica")]
    public Vector3 gridOrigin = Vector3.zero;
    public float velocidad = 3f;

    private bool primerTurno = true;
    private bool esperandoTurno = false;
    private Vector3[] destinos;
    private Vector3[] esquinas;

    [Header("Bomberos (Arrastrar desde la Jerarquía)")]
    public GameObject[] firefighterModels;

    [Header("Prefabs de Entorno (Arrastrar desde tus carpetas)")]
    public GameObject firePrefab;
    public GameObject smokePrefab;
    public GameObject poiHiddenPrefab;
    public GameObject poiVictimPrefab;
    public GameObject damagePrefab;

    private List<GameObject> spawnedEnvironment = new List<GameObject>();

    void Start()
    {
        destinos = new Vector3[firefighterModels.Length];
        esquinas = new Vector3[firefighterModels.Length];

        for (int i = 0; i < firefighterModels.Length; i++)
        {
            if (firefighterModels[i] == null)
            {
                continue;
            }
            destinos[i] = firefighterModels[i].transform.position;
            esquinas[i] = firefighterModels[i].transform.position;
        }
    }

    void Update()
    {
        if (Input.GetKeyDown(KeyCode.Space) && !esperandoTurno)
        {
            esperandoTurno = true;
            StartCoroutine(RequestNextTurn());
        }

        for (int i = 0; i < firefighterModels.Length; i++)
        {
            if (firefighterModels[i] == null)
            {
                continue;
            }

            Vector3 objetivo;
            if (Vector3.Distance(firefighterModels[i].transform.position, esquinas[i]) > 0.3f)
            {
                objetivo = esquinas[i];
            }
            else
            {
                objetivo = destinos[i];
            }

            firefighterModels[i].transform.position = Vector3.MoveTowards(
                firefighterModels[i].transform.position,
                objetivo,
                velocidad * Time.deltaTime);
        }
    }

    IEnumerator RequestNextTurn()
    {
        WWWForm form = new WWWForm();
        form.AddField("action", "next_turn");

        using (UnityWebRequest www = UnityWebRequest.Post(serverUrl, form))
        {
            www.SetRequestHeader("Content-Type", "application/json");
            yield return www.SendWebRequest();

            if (www.result == UnityWebRequest.Result.ConnectionError || www.result == UnityWebRequest.Result.ProtocolError)
            {
                Debug.LogError("Error conectando con Python: " + www.error);
            }
            else
            {
                string jsonResponse = www.downloadHandler.text;
                GameState state = JsonUtility.FromJson<GameState>(jsonResponse);
                Update3DWorld(state);
            }
        }

        esperandoTurno = false;
    }

    void Update3DWorld(GameState state)
    {
        ActualizarPanelAgentes(state);

        if (textoRescatadas != null) textoRescatadas.text = "Victimas Rescatadas: " + state.victims_rescued + " / 7";
        if (textoPerdidas != null) textoPerdidas.text = "Victimas Perdidas: " + state.victims_lost;
        if (textoDanio != null) textoDanio.text = "Daño estructural: " + state.structural_damage + " / 24";
        if (textoTurno != null) textoTurno.text = "Turno: " + state.turn;

        // 1. Mover a los bomberos
        if (state.agents != null)
        {
            foreach (AgentData agent in state.agents)
            {
                int index = agent.id - 1;
                if (index >= 0 && index < firefighterModels.Length)
                {
                    if (firefighterModels[index] != null)
                    {
                        destinos[index] = gridOrigin + new Vector3(agent.x * gridScale, 0, agent.y * gridScale);

                        Vector3 posActual = firefighterModels[index].transform.position;
                        esquinas[index] = new Vector3(posActual.x, destinos[index].y, destinos[index].z);

                        if (primerTurno)
                        {
                            firefighterModels[index].transform.position = destinos[index];
                            esquinas[index] = destinos[index];
                        }
                    }
                }
            }
            primerTurno = false;
        }

        // 2. Limpiar el entorno del turno anterior
        foreach (GameObject obj in spawnedEnvironment)
        {
            Destroy(obj);
        }
        spawnedEnvironment.Clear();

        // 3. Dibujar Fuegos y Humo
        if (state.fires != null)
        {
            foreach (FireData fire in state.fires)
            {
                Vector3 pos = gridOrigin + new Vector3(fire.x * gridScale, 0, fire.y * gridScale);
                GameObject prefabToSpawn = (fire.state == 2) ? firePrefab : smokePrefab;

                if (prefabToSpawn != null)
                {
                    GameObject spawnedObj = Instantiate(prefabToSpawn, pos, Quaternion.identity);
                    spawnedEnvironment.Add(spawnedObj);
                }
            }
        }

        // 4. Dibujar POIs
        if (state.pois != null)
        {
            foreach (PoiData poi in state.pois)
            {
                Vector3 pos = gridOrigin + new Vector3(poi.x * gridScale, 0, poi.y * gridScale);
                GameObject prefabToSpawn = poiHiddenPrefab;

                if (poi.revealed)
                {
                    if (poi.type == "Victim") prefabToSpawn = poiVictimPrefab;
                    else if (poi.type == "FalseAlarm") continue;
                }

                if (prefabToSpawn != null)
                {
                    GameObject spawnedObj = Instantiate(prefabToSpawn, pos, Quaternion.identity);
                    spawnedEnvironment.Add(spawnedObj);
                }
            }
        }

        // 5. Dibujar daño en la estructura
        DrawDamages(state);

        if (state.game_over && panelFinal != null)
        {
            panelFinal.SetActive(true);
            if (textoFinal != null)
            {
                textoFinal.text = state.win ? "¡GANASTE!" : "PERDISTE";
                textoFinal.color = state.win ? Color.green : Color.red;
            }
        }
    }

    void DrawDamages(GameState state)
    {
        if (state.damages == null || damagePrefab == null) return;

        foreach (DamageData d in state.damages)
        {
            if (d.type == "door") continue;

            // Punto medio entre las dos celdas que separa el muro
            float mx = (d.x1 + d.x2) / 2f;
            float my = (d.y1 + d.y2) / 2f;
            Vector3 pos = gridOrigin + new Vector3(mx * gridScale, 0, my * gridScale);

            if (d.x1 == d.x2)
            {
                pos += new Vector3(0, 0, -1.5f);
            }
            else
            {
                pos += new Vector3(1.5f, 0, 0);
            }

            Quaternion rot = (d.x1 == d.x2) ? Quaternion.identity : Quaternion.Euler(0, 90, 0);

            GameObject obj = Instantiate(damagePrefab, pos, rot);
            obj.name = "DMG_" + d.x1 + "_" + d.y1 + "__" + d.x2 + "_" + d.y2;
            spawnedEnvironment.Add(obj);
        }
    }

    void ActualizarPanelAgentes(GameState state)
    {
        if (textoAgentes == null || state.agents == null) return;

        string info = "";
        foreach (AgentData a in state.agents)
        {
            info += "AGENTE " + a.id + ": (" + a.x + "," + a.y + ")";
            info += "  AP: " + a.current_ap;
            info += "  Guardados: " + a.saved_ap;

            if (a.carrying_victim) info += ",  CON VICTIMA";
            if (a.is_knocked_down) info += ",  DERRIBADO";

            info += "\n";
        }
        textoAgentes.text = info;
    }
}