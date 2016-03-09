'use strict';

/* App Module */

var myApp = angular.module('myApp', [
  'ngRoute',
  'myControllers',
  'myServices'
]);

myApp.config(['$routeProvider',
  function($routeProvider) {
    $routeProvider.
      when('/mypins', {
        templateUrl: 'templates/mypins.html',
        controller: 'MyPinsCtrl'
      }).
      when('/publicpins', {
        templateUrl: 'templates/publicpins.html',
        controller: 'PublicPinsCtrl'
      }).
      when('/addpin', {
        templateUrl: 'templates/addpin.html',
        controller: 'AddPinCtrl'
      }).
      when('/login', {
        templateUrl: 'templates/login.html',
        controller: 'LoginCtrl'
      }).
      when('/createacct', {
        templateUrl: 'templates/createacct.html',
        controller: 'CreateAcctCtrl'
      }).
      otherwise({
        redirectTo: '/createacct'
      });
  }]);
