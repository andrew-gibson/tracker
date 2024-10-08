from . import models


def good_m2m_request(user, method, obj1, obj2, attr):

    match [obj1, obj2, attr, method]:
        case [models.Project(), models.ProjectUser(), "viewers", "POST" | "DELETE"]:
            # allow a user to add itself as a viewer of a project normally outside its group
            return obj2.pk == user.pk
        case _:
            # default to seeing if user has permission to post to the first object
            # and can read the linked object
            return good_request(user, "POST", obj1) and good_request(user, "GET", obj2)


def good_request(user, method, obj):


    match [obj, method]:


        case [models.ProjectGroup(), "POST"] if not obj.id:
            # only group alterations are allowed by the group owner
            return bool(user.manages)

        case [models.ProjectGroup(), "POST" | "PUT" | "DELETE"]:
            # only group alterations are allowed by the group owner
            p1 =  obj.app == "project"
            p2 =  bool(user.manages)
            return  p1 and p2 and  (obj in user.manages.descendants)

        case [
            models.ProjectGroup() | models.EXCompetency() | models.ProjectStatus(),
            "GET",
        ]:
            # return group info to all users
            return True

        case [models.MyProjectGroup(), "GET"]:
            return True

        case [
            models.EXCompetency() | models.ProjectStatus(),
            "POST" | "PUT" | "DELETE",
        ]:
            # don't allow any projectuser, competency or status alterations through this app
            return False

        case [models.ProjectUser(), "POST"] if not obj.id:
            return bool(user.manages)

        case [models.ProjectUser(), "POST"]:
            return (
                user.manages == obj.belongs_to
                or obj.belongs_to in user.manages.descendants
                or user.pk == obj.pk
            )

        case [models.ProjectUser(), "PUT" | "DELETE"]:
            # only for users who manage a group in the reporting chain
            return user.manages and obj.belongs_to in user.manages.descendants

        case [models.ProjectUser(), "GET"]:
            # only return user info to the request user
            return (
                user.pk == obj.pk
                or (user.manages and obj.belongs_to in user.manages.descendants)
                or user.belongs_to == obj.belongs_to
            )

        case [models.Tag(), "POST"]:
            # only tag alterations are allowed by the group members
            return True

        case [models.Tag(), "PUT" | "DELETE"]:
            # only tag alterations are allowed by the group members
            return (obj not in models.Tag.eisenhower_tags() 
                    and  obj.group in user.belongs_to.descendants)

        case [models.Tag(), "GET"]:
            # only tag reads are allowed by the group members except for public tags
            return (obj.group in user.belongs_to.descendants) or obj.public

        case [models.Stream() | models.Task(), "POST"] if not obj.id:
            # can a user in general create a blank version of these objects?
            # return None to indicate that it's depends
            try:
                return good_project_request(user, method, obj.project)
            except obj.__class__.project.RelatedObjectDoesNotExist:
                return None

        case [ models.Stream() , "PUT" | "DELETE" ] if obj.project_default:
            # default to the owner project for permissions
            #if "project" not in obj._state.fields_cache:
            #    import pdb
            #    pdb.set_trace()

            return False
        case [ models.Link(), "POST"  ] if not obj.id:
            return True

        case [
            models.Stream() | models.Task() | models.Link(),
            "POST" | "PUT" | "DELETE" | "GET",
        ]:

            # default to the owner project for permissions
            #if "project" not in obj._state.fields_cache:
            #    import pdb
            #    pdb.set_trace()

            return good_project_request(user, method, obj.project)

        case [ models.Project(), "POST" ] if not obj.id:
            return True
        case [
            models.Project(),
            "POST" | "PUT" | "DELETE" | "GET",
        ]:
            # see good_project_request for descriptions of permissions
            return good_project_request(user, method, obj)

        case [
            models.Log() | models.TimeReport(),
            "GET" | "PUT" | "DELETE",
        ]:
            # Logentry and TimeReport belong exclusively to the owning users
            return user == obj.user
        case [models.Log() | models.TimeReport(), "POST"]:
            # Logentry and TimeReport belong exclusively to the owning users
            return True
        case [models.Settings() , "POST" | "GET" | "PUT"]:
            return True
        case [models.ProjectType() ,  "GET" ]:
            return True
        case _:
            # default is no permission
            return False


def good_project_request(user, method, project):
    if method in ["PUT", "POST", "DELETE"]:
        return (project.private and project.private_owner == user) or (
            project.group in user.belongs_to.descendants
        )
    else:
        return (
            project.private and project.private_owner == user
        ) or not project.private  ## is private owner
