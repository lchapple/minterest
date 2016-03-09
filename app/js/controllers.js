'use strict';


var myControllers = angular.module('myControllers', []);

myControllers.controller('AppCtrl', ['$scope', '$rootScope',
    function($scope, $rootScope) {
        $rootScope.user_id = '';
        $rootScope.user_name = '';
    }]);

myControllers.controller('MyPinsCtrl', ['$scope', '$rootScope', '$location', 'UserPins', 'UserPin',
    function($scope, $rootScope, $location, UserPins, UserPin) {
        if ($rootScope.user_id == '') {
            $scope.pins = [];
            $location.path('/login'+'?next='+$location.path());
        } else {
            UserPins.get({user_id: $rootScope.user_id}, function(pinset) {
                // Tornado refuses to write out an array to json, only a dict so make it an array
                var pid;
                $scope.pins = [];
                for (pid in pinset) {
                    if (typeof pinset[pid] === "object" && pinset[pid].content != undefined) {
                        $scope.pins.push(pinset[pid]);
                    }
                }
            });
        }

        $scope.goto = function(loc) {
            $location.path(loc);
        };

        $scope.unpin = function(pin_id) {
            UserPin.remove({user_id: $rootScope.user_id, pin_id: pin_id}, function() {
                // this is a temporary hack -- reload the list from scratch when should instead find the one that
                // was deleted in $scope.pins and delete it from there directly
                UserPins.get({user_id: $rootScope.user_id}, function(pinset) {
                    // Tornado refuses to write out an array to json, only a dict so make it an array
                    var pid;
                    $scope.pins = [];
                    for (pid in pinset) {
                        if (typeof pinset[pid] === "object" && pinset[pid].content != undefined) {
                            $scope.pins.push(pinset[pid]);
                        }
                    }
                });
            })
        };
    }]);

myControllers.controller('PublicPinsCtrl', ['$scope', '$rootScope', '$location', 'UserPins', 'AllPins',
    function($scope, $rootScope, $location, UserPins, AllPins) {
        AllPins.get({}, function(pinset) {
            // Tornado refuses to write out an array to json, only a dict so make it an array
            var pid;
            $scope.pins = [];
            for (pid in pinset) {
                if (typeof pinset[pid] === "object" && pinset[pid].content != undefined) {
                    $scope.pins.push(pinset[pid]);
                }
            }
        });

        $scope.goto = function(loc) {
            $location.path(loc);
        };

        $scope.addToMyPins = function(pin_id) {
            var user_id = $rootScope.user_id || '';
            if (user_id == '') {
                $location.path('/login'+'?next='+$location.path());
            } else {
                UserPins.save({user_id: user_id}, {pin_id: pin_id}, function(pin_id) {
                });
            }
        };
    }]);

myControllers.controller('AddPinCtrl', ['$scope', '$rootScope', '$location', 'UserPins',
    function($scope, $rootScope, $location, UserPins) {
        $scope.content = 'http://';
        $scope.image = 'http://';
        $scope.title = '';
        $scope.caption = '';
        $scope._private = false;

        $scope.submit = function() {
            var user_id = $rootScope.user_id || '';
            if (user_id == '') {
                $location.path('/login'+'?next='+$location.path());
            } else {
                UserPins.save({user_id: user_id},
                              {content: $scope.content,
                                  image: $scope.image,
                                  title: $scope.title,
                                  caption: $scope.caption,
                                  private: $scope._private},
                    function(pin) {
                        $location.path('/mypins');
                    });
            }
        };
    }]);

myControllers.controller('LoginCtrl', ['$scope', '$rootScope', '$location', 'Users',
    function($scope, $rootScope, $location, Users) {
        $rootScope.user_id = '';
        $rootScope.user_name = '';
        $scope.name = '';
        $scope.pw = '';
        $scope.next = $location.search().next || '';
        $scope.form_error = '';

        $scope.submit = function() {
            Users.get({name: $scope.name, pw: $scope.pw},
                function(user) {
                    var next = $scope.next != '' ? $scope.next : '/mypins';
                    $rootScope.user_id = user.id;
                    $rootScope.user_name = user.name;
                    $scope.form_error = '';
                    $location.path(next);
                },
                function(error) {
                    $scope.name = '';
                    $scope.pw = '';
                    if (error.status == 401) {
                        $scope.form_error = "incorrect name or password, try again";
                    } else {
                        $scope.form_error = error.statusText;
                    }
                }
            );
        };
    }]);

myControllers.controller('CreateAcctCtrl', ['$scope', '$rootScope', '$location', 'Users',
    function($scope, $rootScope, $location, Users) {
        $rootScope.user_id = '';
        $scope.name = '';
        $scope.pw = '';
        $scope.next = $location.search().next || '';
        $scope.form_error = '';

        $scope.submit = function() {
            Users.save({}, {name: $scope.name, pw: $scope.pw},
                function(user) {
                    var next = $scope.next != '' ? $scope.next : '/mypins';
                    $rootScope.user_id = user.id;
                    $rootScope.user_name = user.name;
                    $scope.form_error = '';
                    $location.path(next);
                },
                function(error) {
                    $scope.name = '';
                    $scope.pw = '';
                    if (error.status == 409) {
                        $scope.form_error = "account already exists, go to login";
                    } else {
                        $scope.form_error = error.statusText;
                    }
                }
            );
        };
    }]);




