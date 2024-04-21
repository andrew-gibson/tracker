const headers =  {  'X-CSRFToken' : csrf_token,  'Content-Type': 'application/json' };
const fetch_recipies = {
    csrf_token,
    headers,
    GET : async (url, json_response = false,) => {
        return await fetch( url, {headers : {'json-response' : json_response.toString(),...headers}});
    },
    GETjson :  async (url,json_response = true) => {
        return await (await fetch_recipies.GET(url)).json();
    },               
    PUT : async (url, body, json_response = false, ) => {
        const headers = {
            'X-CSRFToken' : csrf_token, 
            'json-response' : json_response.toString(),
           'Content-Type': 'application/x-www-form-urlencoded'
        };
        return await fetch( url, {method: "PUT",headers, body});
    },
    POST : async (url, body, json_response = false, ) => {
        const headers = {
            'X-CSRFToken' : csrf_token, 
            'json-response' : json_response.toString(),
            'Content-Type': 'application/x-www-form-urlencoded'
        };
        return await fetch( url, {method: "POST",headers, body});
    },
     DELETE : async (url) => {
        return await fetch( url, {method: "DELETE",headers  });
    }
};
export default fetch_recipies;
