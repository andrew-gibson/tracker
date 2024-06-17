from . import models


def good_m2m_request(user, method,obj1,obj2,attr):
    match [obj1, obj2,attr,method]:
        case [models.Project(), models.ProjectUser(),"viewers", "POST" | "DELETE"]:
            # allow a user to add itself as a viewer of a project normally outside its group
            return obj2.pk == user.pk
        case _:
            # default to usual permission access to each individual object
            return  good_request(user,method,obj1) and good_request(user,method,obj2)


def good_request(user, method,obj):
    match [obj, method]:
        case [models.ProjectGroup(), "POST" | "PUT" | "DELETE"]:
            # only group alterations are allowed by the group owner
            return ( obj.app == "project"
                     and (user.manages in [obj,*obj.parents])
                    )

        case [models.ProjectGroup() | models.EXCompetency() | models.ProjectStatus(), "GET"]:
            # return group info to all users
            return True

        case [models.EXCompetency() | models.ProjectStatus(), "POST" | "PUT" | "DELETE"]:
            #don't allow any projectuser, competency or status alterations through this app
            return False

        case  [models.ProjectUser() ,"POST" | "PUT" | "DELETE"]:
            # only for users who manage a group in the reporting chain
            return user.manages in [obj.belongs_to, *obj.belongs_to.parents ]

        case [models.ProjectUser(), "GET"]:
            # only return user info to the request user
            return (  user.manages in [obj,*obj.belongs_to.parents]
                      or  user.belongs_to == obj.belongs_to
                    )


        case [models.Tag(), "POST" | "PUT" | "DELETE"]:
            # only tag alterations are allowed by the group members
            return obj.group in user.groups.all()

        case [models.Tag(), "GET"]:
            # only tag reads are allowed by the group members except for public tags
            return (obj.group in user.groups.all()) or obj.public

        case [
            models.Stream() | models.Task() | models.ProjectLog(),
            "POST" | "PUT" | "DELETE" | "GET",
        ]:
            # default to the owner project for permissions
            return good_project_request(user,method, obj.project)

        case [
            models.Project() | models.MinProject(),
            "POST" | "PUT" | "DELETE" | "GET",
        ]:
            # see good_project_request for descriptions of permissions
            return good_project_request(user,method, obj)

        case [
            models.ProjectLogEntry() | models.TimeReport(),
            "GET" | "POST" | "PUT" | "DELETE",
        ]:
            # Logentry and TimeReport belong exclusively to the owning users 
            return user == obj.user

        case _:
            # default is no permission
            return False


def good_project_request(user, method, project):
    if method in ["PUT", "POST", "DELETE"]:
        return (
            (project.private and project.private_owner == user) 
            or (project.group in user.groups.all())
        )
    else:
        return (
            (project.private and project.private_owner == user)     ## is private owner
            or (user in project.viewers.all())   ## is viewing the project
            or (project.group in user.groups.all())  ## user manages the group which owns the project
        )
