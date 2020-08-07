(function (
  document,

  GRAPHENE_SETTINGS,
  GraphiQL,
  React,
  ReactDOM,
  SubscriptionsTransportWs,
  fetch,
  history,
  location,
) {
  // Parse the cookie value for a CSRF token
  var csrftoken;
  var cookies = ("; " + document.cookie).split("; csrftoken=");
  if (cookies.length == 2) {
    csrftoken = cookies.pop().split(";").shift();
  } else {
    csrftoken = document.querySelector("[name=csrfmiddlewaretoken]").value;
  }

  // Collect the URL parameters
  var parameters = {};
  location.hash
    .substr(1)
    .split("&")
    .forEach(function (entry) {
      var eq = entry.indexOf("=");
      if (eq >= 0) {
        parameters[decodeURIComponent(entry.slice(0, eq))] = decodeURIComponent(
          entry.slice(eq + 1),
        );
      }
    });
  // Produce a Location fragment string from a parameter object.
  function locationQuery(params) {
    return (
      "#" +
      Object.keys(params)
        .map(function (key) {
          return (
            encodeURIComponent(key) + "=" + encodeURIComponent(params[key])
          );
        })
        .join("&")
    );
  }
  // Derive a fetch URL from the current URL, sans the GraphQL parameters.
  var graphqlParamNames = {
    query: true,
    variables: true,
    operationName: true,
  };
  var otherParams = {};
  for (var k in parameters) {
    if (parameters.hasOwnProperty(k) && graphqlParamNames[k] !== true) {
      otherParams[k] = parameters[k];
    }
  }

  var fetchURL = locationQuery(otherParams);

  // Defines a GraphQL fetcher using the fetch API.
  function httpClient(graphQLParams, opts) {
    if (typeof opts === 'undefined') {
      opts = {};
    }
    var headers = opts.headers || {};
    headers['Accept'] = headers['Accept'] || 'application/json';
    headers['Content-Type'] = headers['Content-Type'] || 'application/json';
    if (csrftoken) {
      headers['X-CSRFToken'] = csrftoken
    }
    return fetch(fetchURL, {
      method: "post",
      headers: headers,
      body: JSON.stringify(graphQLParams),
      credentials: "include",
    })
      .then(function (response) {
        return response.text();
      })
      .then(function (responseBody) {
        try {
          return JSON.parse(responseBody);
        } catch (error) {
          return responseBody;
        }
      });
  }

  // Derive the subscription URL. If the SUBSCRIPTION_URL setting is specified, uses that value. Otherwise
  // assumes the current window location with an appropriate websocket protocol.
  var subscribeURL =
    location.origin.replace(/^http/, "ws") +
    (GRAPHENE_SETTINGS.subscriptionPath || location.pathname);

  // Create a subscription client.
  var subscriptionClient = new SubscriptionsTransportWs.SubscriptionClient(
    subscribeURL,
    {
      // Reconnect after any interruptions.
      reconnect: true,
      // Delay socket initialization until the first subscription is started.
      lazy: true,
    },
  );

  // Keep a reference to the currently-active subscription, if available.
  var activeSubscription = null;

  // Define a GraphQL fetcher that can intelligently route queries based on the operation type.
  function graphQLFetcher(graphQLParams, opts) {
    var operationType = getOperationType(graphQLParams);

    // If we're about to execute a new operation, and we have an active subscription,
    // unsubscribe before continuing.
    if (activeSubscription) {
      activeSubscription.unsubscribe();
      activeSubscription = null;
    }

    if (operationType === "subscription") {
      return {
        subscribe: function (observer) {
          subscriptionClient.request(graphQLParams).subscribe(observer);
          activeSubscription = subscriptionClient;
        },
      };
    } else {
      return httpClient(graphQLParams, opts);
    }
  }

  // Determine the type of operation being executed for a given set of GraphQL parameters.
  function getOperationType(graphQLParams) {
    // Run a regex against the query to determine the operation type (query, mutation, subscription).
    var operationRegex = new RegExp(
      // Look for lines that start with an operation keyword, ignoring whitespace.
      "^\\s*(query|mutation|subscription)\\s*" +
        // The operation keyword should be followed by whitespace and the operationName in the GraphQL parameters (if available).
        (graphQLParams.operationName ? ("\\s+" + graphQLParams.operationName) : "") +
        // The line should eventually encounter an opening curly brace.
        "[^\\{]*\\{",
      // Enable multiline matching.
      "m",
    );
    var match = operationRegex.exec(graphQLParams.query);
    if (!match) {
      return "query";
    }

    return match[1];
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
    headerEditorEnabled: GRAPHENE_SETTINGS.graphiqlHeaderEditorEnabled,
    query: parameters.query,
  };
  if (parameters.variables) {
    options.variables = parameters.variables;
  }
  if (parameters.operation_name) {
    options.operationName = parameters.operation_name;
  }
  // Render <GraphiQL /> into the body.
  ReactDOM.render(
    React.createElement(GraphiQL, options),
    document.getElementById("editor"),
  );
})(
  document,

  window.GRAPHENE_SETTINGS,
  window.GraphiQL,
  window.React,
  window.ReactDOM,
  window.SubscriptionsTransportWs,
  window.fetch,
  window.history,
  window.location,
);
