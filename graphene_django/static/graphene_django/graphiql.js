(function() {
  // Parse the cookie value for a CSRF token
  var csrftoken;
  var cookies = document.cookie.split(';').reduce((p, c) => {
    var x = {};
    var key = c.split('=')[0].trim();
    var value = c.split('=')[1]
    x[key] = p[key] ? p[key].concat([value]) : [value];
    return Object.assign(p, x);
  }, {});
  // Collect the URL parameters
  var parameters = {};
  window.location.hash
    .substr(1)
    .split('&')
    .forEach(function(entry) {
      var eq = entry.indexOf('=');
      if (eq >= 0) {
        parameters[decodeURIComponent(entry.slice(0, eq))] = decodeURIComponent(entry.slice(eq + 1));
      }
    });
  // Produce a Location fragment string from a parameter object.
  function locationQuery(params) {
    return (
      '#' +
      Object.keys(params)
        .map(function(key) {
          return encodeURIComponent(key) + '=' + encodeURIComponent(params[key]);
        })
        .join('&')
    );
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
      Accept: 'application/json',
      'Content-Type': 'application/json'
    };
    if (cookies.csrftoken && cookies.csrftoken.length) {
      headers['X-CSRFToken'] = cookies.csrftoken.pop();
    }
    function getFetch(headers) {
      return fetch(fetchURL, {
        method: 'post',
        headers: headers,
        body: JSON.stringify(graphQLParams),
        credentials: 'include'
      });
    }
    return getFetch(headers)
      .then(function(response) {
        console.log(headers);
        return response.text();
      })
      .then(function(responseBody) {
        try {
          return JSON.parse(responseBody);
        } catch (error) {
          if (cookies.csrftoken.length) {
            headers['X-CSRFToken'] = cookies.csrftoken.pop();
            return getFetch(headers);
          }
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
    query: parameters.query
  };
  if (parameters.variables) {
    options.variables = parameters.variables;
  }
  if (parameters.operation_name) {
    options.operationName = parameters.operation_name;
  }
  // Render <GraphiQL /> into the body.
  ReactDOM.render(React.createElement(GraphiQL, options), document.body);
})();
