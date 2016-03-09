'use strict';

var myServices = angular.module('myServices', ['ngResource']);

myServices.factory('Users', ['$resource',
  function($resource){
    return $resource('/api/v1/users', {});
  }]);

myServices.factory('User', ['$resource',
  function($resource){
    return $resource('/api/v1/users/:user_id', {});
  }]);

myServices.factory('UserPins', ['$resource',
  function($resource){
    return $resource('/api/v1/users/:user_id/pins', {});
  }]);

myServices.factory('UserPin', ['$resource',
  function($resource){
    return $resource('/api/v1/users/:user_id/pins/:pin_id', {});
  }]);

myServices.factory('AllPins', ['$resource',
  function($resource){
    return $resource('/api/v1/pins', {});
  }]);
