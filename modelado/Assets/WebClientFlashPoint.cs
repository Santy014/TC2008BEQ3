using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Networking;

[System.Serializable]
public class AgentData
{
    public int id;
    public int x;
    public int y;
    public bool carrying_victim;
    public bool is_knocked_down;
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
public class GameState
{
    public int turn;
    public int structural_damage;
    public int victims_rescued;
    public int victims_lost;
    public AgentData[] agents;
    public FireData[] fires;
    public PoiData[] pois;
}

public class WebClientFlashPoint : MonoBehaviour
{
    [Header("Configuración del Servidor")]
    public string serverUrl = "http://localhost:8585";
    
    [Header("Ajustes del Tablero")]
    public float gridScale = 2.0f;
    [Tooltip("Coordenada XYZ real en Unity donde se ubica la casilla (0,0) lógica")]
    public Vector3 gridOrigin = Vector3.zero;
    public float velocidad = 3f;


    private bool primerTurno = true;
    private Vector3[] destinos;
    [Header("Bomberos (Arrastrar desde la Jerarquía)")]
    public GameObject[] firefighterModels;
    
    [Header("Prefabs de Entorno (Arrastrar desde tus carpetas)")]
    public GameObject firePrefab;
    public GameObject smokePrefab;
    public GameObject poiHiddenPrefab;
    public GameObject poiVictimPrefab;

    private List<GameObject> spawnedEnvironment = new List<GameObject>();

    void Start() 
    {
    destinos = new Vector3[firefighterModels.Length];
    
    for (int i = 0; i < firefighterModels.Length; i++) 
        {
            if (firefighterModels[i] == null)
            {
             continue;   
            }
        destinos[i] = firefighterModels[i].transform.position;   
        }
    }
    
    void Update()
    {
        if (Input.GetKeyDown(KeyCode.Space))
        {
            StartCoroutine(RequestNextTurn());
        }
            for (int i = 0; i < firefighterModels.Length; i++) 
        {
            if (firefighterModels[i] == null)
            {
             continue;   
            }
        firefighterModels[i].transform.position = Vector3.MoveTowards(firefighterModels[i].transform.position, destinos[i], velocidad * Time.deltaTime);
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
    }

    void Update3DWorld(GameState state)
    {
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
                        // Se suma el gridOrigin para compensar la posición real de la casa
                        destinos[index] = gridOrigin + new Vector3(agent.x * gridScale, 0, agent.y * gridScale);
                        if (primerTurno) 
                        {
                            firefighterModels[index].transform.position = destinos[index];
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
                    if (poi.type == "victim") prefabToSpawn = poiVictimPrefab;
                    else if (poi.type == "false_alarm") continue; 
                }

                if (prefabToSpawn != null)
                {
                    GameObject spawnedObj = Instantiate(prefabToSpawn, pos, Quaternion.identity);
                    spawnedEnvironment.Add(spawnedObj);
                }
            }
        }
    }
}