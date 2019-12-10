(function() {

  // Parse the cookie value for a CSRF token
  var csrftoken;
  var cookies = ('; ' + document.cookie).split('; csrftoken=');
  if (cookies.length == 2) {
    csrftoken = cookies.pop().split(';').shift();
  } else {
    csrftoken = document.querySelector("[name=csrfmiddlewaretoken]").value;
  }

  // Collect the URL parameters
  var parameters = {};
  window.location.hash.substr(1).split('&').forEach(function (entry) {
    var eq = entry.indexOf('=');
    if (eq >= 0) {
      parameters[decodeURIComponent(entry.slice(0, eq))] =
        decodeURIComponent(entry.slice(eq + 1));
    }
  });
  // Produce a Location fragment string from a parameter object.
  function locationQuery(params) {
    return '#' + Object.keys(params).map(function (key) {
      return encodeURIComponent(key) + '=' +
        encodeURIComponent(params[key]);
    }).join('&');
  }
  // Derive a fetch URL from the current URL, sans the GraphQL parameters.
  var graphqlParamNames = {
    query: true,
    variables: true,
    operationName: true
  };
  var otherParams = {};
  for (var k in parameters) {
    if (parameters.hasOwnProperty(k) && graphqlParamNames[k] !== true) {
      otherParams[k] = parameters[k];
    }
  }

  var fetchURL = locationQuery(otherParams);

  // Defines a GraphQL fetcher using the fetch API.
  function graphQLFetcher(graphQLParams) {
    var headers = {
      'Accept': 'application/json',
      'Content-Type': 'application/json'
    };
    if (csrftoken) {
      headers['X-CSRFToken'] = csrftoken;
    }
    return fetch(fetchURL, {
      method: 'post',
      headers: headers,
      body: JSON.stringify(graphQLParams),
      credentials: 'include',
    }).then(function (response) {
      return response.text();
    }).then(function (responseBody) {
      try {
        return JSON.parse(responseBody);
      } catch (error) {
        return responseBody;
      }
    });
  }
  // When the query and variables string is edited, update the URL bar so
  // that it can be easily shared.
  function onEditQuery(newQuery) {
    parameters.query = newQuery;
    updateURL();
  }
  function onEditVariables(newVariables) {
    parameters.variables = newVariables;
    updateURL();
  }
  function onEditOperationName(newOperationName) {
    parameters.operationName = newOperationName;
    updateURL();
  }
  function updateURL() {
    history.replaceState(null, null, locationQuery(parameters));
  }
  var options = {
    fetcher: graphQLFetcher,
      onEditQuery: onEditQuery,
      onEditVariables: onEditVariables,
      onEditOperationName: onEditOperationName,
      query: parameters.query,
  }
  if (parameters.variables) {
    options.variables = parameters.variables;
  }
  if (parameters.operation_name) {
    options.operationName = parameters.operation_name;
  }
  // Render <GraphiQL /> into the body.
  ReactDOM.render(
    React.createElement(GraphiQL, options),
    document.body
  );
})();
